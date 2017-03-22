""" Desktop management (window grouping) for footwm. """

from . import command
from . import ewmh
from . import xlib
from . import log as logmodule

log = logmodule.make(name=__name__)

class Desktop:
    """ Manage user created desktops, plus the null & unassigned desktops. """

    def __init__(self, display, root):
        """ Desktops are built from root child windows. """
        self.display = display
        self.root = root
        self._commander = command.FootCommandWM(self.display, self.root, self)
        self._unassigned = 'Unassigned'
        self._specials = [self._unassigned]
        # Keep the order of desktops: [desktop-name]
        self._desklist = self._specials[:]
        # Dict(desktop-name, [window])
        self._deskwins = {k: [] for k in self._desklist}
        self.ewmh = ewmh.EwmhWM(self.display, self.root)
        self._makeunassigned()
        self._updatedesktophints()
        self._currentdesk = None
        self.selectdesktop(0)

    def oncommand(self):
        """ Handle command received from a client. """
        self._commander.action()

    def adddesktop(self, name, index=0):
        """ Add a new desktop with name. Name must be unique. """
        if name in self._deskwins:
            log.error('%s exists. Desktop names must be unique', name)
        else:
            self._desklist.insert(index, name)
            self._deskwins[name] = []
            if index == 0:
                # Select the desktop.
                self.selectdesktop(index)
            else:
                self._updatedesktophints()

    def selectdesktop(self, index):
        # Ensure that that the first (current) entry is not selected.
        #if index != 0 and index != -len(self._desklist):
        try:
            deskname = self._desklist[index]
        except IndexError:
            pass
        else:
            if deskname != self._currentdesk:
                # The desktop order will be changed.
                # Hides all the windows of the *previously drawn desktop*. Note the use of _currentdesk.
                # This is because add/delete etc will have already changed the desktop order.
                for w in self._deskwins.get(self._currentdesk, []):
                    # XXX Check that the window is not already visible before hiding...
                    w.hide()
                self._desklist.pop(index)
                self._desklist.insert(0, deskname)
                self._updatedesktophints()
                self._updatewindowhints()
                self._currentdesk = deskname
                self.redraw()

    def deletedesktop(self, index):
        # Update ewmh desktop atoms.
        try:
            deskname = self._desklist[index]
        except IndexError:
            pass
        else:
            # Only allow deleting regular (non-special) desktops.
            if deskname not in self._specials:
                # Move windows from the deleted desktop to the unassigned desktop.
                udesk = self._deskwins[self._unassigned]
                for w in self.stacklist:
                    udesk.append(w)
                del self._desklist[index]
                del self._deskwins[deskname]
                if index == 0:
                    self.selectdesktop(index)
                else:
                    self._updatedesktophints()

    def renamedesktop(self, index, newname):
        """ Renames the selected desktop. """
        if newname in self._deskwins:
            log.error('%s exists. Cannot rename deskop, names must be unique.', newname)
        else:
            try:
                oldname = self._desklist.pop(index)
            except IndexError:
                pass
            else:
                self._desklist.insert(index, newname)
                desk = self._deskwins.pop(oldname)
                self._deskwins[newname] = desk
                if oldname == self._currentdesk:
                    self._currentdesk = newname
                # Allow renaming special desktops.
                if self._unassigned == oldname:
                    self._unassigned = newname
                self._updatedesktophints()

    @property
    def clientlist(self):
        """ Client list of windows in creation order. """
        return [window for windowid, window in self.root.children.items() if window in self.stacklist]

    @property
    def stacklist(self):
        """ Usage order of windows in current desktop. """
        # Get the windows for the current desktop.
        return self._deskwins[self._desklist[0]]

    def _makeunassigned(self):
        """ Import windows that look like they'll need to be managed into the unassigned group. """
        stacklist = [w for w in self.root.children.values() if managewindowp(w)]
        self._deskwins[self._unassigned] = stacklist
        for window in stacklist:
            log.debug('0x%08x: importing window %s', window.window, window)
            # Manage imported windows.
            window.manage(xlib.InputEventMask.StructureNotify)

    def managewindow(self, window):
        if not window.override_redirect:
            # Put window to the top of the list and update display.
            # XXX Is this check needed?
            if window not in self.stacklist:
                i = 0
                self.stacklist.insert(i, window)
            window.manage(xlib.InputEventMask.EnterWindow | xlib.InputEventMask.FocusChange | xlib.InputEventMask.StructureNotify)
            self.raisewindow(window)
            self.redraw()

    def unmanagewindow(self, win):
        """ Remove the window from window lists. """
        del self.root.children[win.window]
        # Remove from our own managed lists, and from the ewmh properties.
        # XXX Check if the window was part of the current desktop and visible!
        doredraw = False
        for dname, dwins in self._deskwins.items():
            if win in dwins:
                dwins.remove(win)
                if dname == self._desklist[0]:
                    doredraw = True
        else:
            # Window not found... Maybe log an internal error?
            pass

        if doredraw:
            self._updatewindowhints()
            self.redraw()

    def _updatedesktophints(self):
        """ Update desktop atoms, eg ewmh desktop number and desktop names. """
        self.ewmh.desktopnames = self._desklist

    def _updatewindowhints(self):
        """ Update ewmh client window lists. """
        self.ewmh.clientlist = self.clientlist
        self.ewmh.clientliststacking = self.stacklist

    def raisewindow(self, win):
        """ Select the family of windows that belong to the window. """
        # family accounts for transients
        # TODO window groups. See ICCCM 4.1.11
        # XXX Automatically select group if the window is in a different group?
        # XXX Maybe not, how to handle case where the window is in multiple groups?
        if win in self.stacklist:
            for w in win.family:
                self.stacklist.remove(w)
            for w in reversed(win.family):
                self.stacklist.insert(0, w)
            self._updatewindowhints()

    def redraw(self):
        """ Redraw all visible windows. Any parents of transient windows will also be shown. """
        try:
            family = self.stacklist[0].family
        except IndexError:
            log.warning('0x{:08x}: show stacklist is empty.'.format(self.root.window))
            family = []
        # Focus the very top window.
        if family:
            w = family[0]
            # TODO use a layout object to decide ideal window size.
            w.resize(self.root.geom)
            w.show()
            self.ewmh.activewindow = w
            log.debug('0x%08x: showing window=%s', w.window, w)
        # Hide every window that's not in the family of windows.
        for w in self.stacklist:
            if w not in family:
                log.debug('0x%08x: hiding %s', w.window, w)
                # XXX only hide visible windows!!
                w.hide()

    def withdrawwindow(self, win):
        if win.window in self.stacklist:
            # X has unmapped the window, we can now put it in the withdrawn state.
            # Mark window Withdrawn. See ICCCM 4.1.3.1
            win.wm_state = xlib.WmStateState.Withdrawn
            log.debug('0x%08x: Unmap successful %s', e.window, win)
            # Since the window has been unmapped(hidden) show the next window in the list.
            self.redraw()

def managewindowp(win):
    """ manage-window-predicate. Return True if the window should be managed, False otherwise. """
    # Never manage cases where override_redirect=True.
    # We have two extra restrictions when importing windows at program startup.
    # Allow import of windows that have MapState=IsViewable, or WM_STATE exists.
    # This is because X has an extra restriction about windows to manage. ie, X apps can create children of the
    # root window, with their override_redirect=False but never Map them and the window manager then has to ignore them.
    # With these checks we're assuming that IsViewable means the window will want to Map itself or that a prior window
    # manager decided to manage the window and added a WM_STATE attribute so we'll manage it too.
    if win.map_state == xlib.MapState.IsViewable:
        manage = True
    elif win.wm_state:
        manage = True
    elif win.override_redirect:
        manage = False
    else:
        manage = False
    return manage
