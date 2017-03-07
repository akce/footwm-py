""" Desktop management (window grouping) for footwm. """

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
        self._makestacklist()
        self.ewmh = ewmh.EwmhWM(self.display, self.root)
        self.ewmh.clientlist = self.clientlist
        self.ewmh.clientliststacking = self.stacklist

    def add(self, name, pos=0):
        """ Add a new desktop with name. Name must be unique. A new desktop object is returned. """
        pass

    @property
    def clientlist(self):
        """ Client list of windows in creation order. """
        return [window for windowid, window in self.root.children.items() if window in self.stacklist]

    def _makestacklist(self):
        """ Import windows into stacklist that look like they'll need to be managed. """
        self.stacklist = [w for w in self.root.children.values() if managewindowp(w)]
        for window in self.stacklist:
            log.debug('0x%08x: importing window %s', window.window, window)
            # Manage imported windows.
            window.manage(xlib.InputEventMask.StructureNotify)

    def managewindow(self, window):
        if not window.override_redirect:
            # Put window to the top of the list and update display.
            if window not in self.stacklist:
                i = 0
                self.stacklist.insert(i, window)
            window.manage(xlib.InputEventMask.EnterWindow | xlib.InputEventMask.FocusChange | xlib.InputEventMask.StructureNotify)
            self.show(win=window)
            self.ewmh.clientlist = self.clientlist
            self.ewmh.clientliststacking = self.stacklist

    def unmanagewindow(self, win):
        """ Remove the window from window lists. """
        del self.root.children[win.window]
        # Remove from our own managed lists, and from the ewmh properties.
        try:
            self.stacklist.remove(win)
        except ValueError:
            pass
        else:
            self.ewmh.clientlist = self.clientlist
            self.ewmh.clientliststacking = self.stacklist
            self.show()

    def _movetofront(self, win):
        """ Select the family of windows that belong to the window. """
        # family accounts for transients
        # TODO window groups. See ICCCM 4.1.11
        family = win.family
        for w in family:
            self.stacklist.remove(w)
        for w in reversed(family):
            self.stacklist.insert(0, w)
        self.ewmh.clientliststacking = self.stacklist
        return family

    def show(self, win=None):
        """ Pick a child window to bring to front. Any parents of transient windows will also be shown. """
        if win is None:
            # Redraw with the first window's family when win isn't given.
            try:
                family = self.clientlist[0].family
            except IndexError:
                log.warning('0x{:08x}: show clientlist is empty.'.format(self.root.window))
                family = []
        else:
            family = self._movetofront(win=win)
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
            self.show()

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
