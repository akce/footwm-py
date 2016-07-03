"""
Main footwm module.

Copyright (c) 2016 Akce
"""

# Python standard modules.
import logging

# Local modules.
import footwm.xlib as xlib
from . import display
from . import ewmh
from . import window
from . import xevent
import footwm.log

log = footwm.log.make(name=__name__)

class Foot(object):

    def __init__(self, displayname=None):
        self.display = display.Display(displayname)
        log.debug('%s: connect display=%s', self.__class__.__name__, self.display)
        # TODO: worry about screens, displays, xrandr and xinerama!
        self.root = window.RootWindow(self.display, self.display.defaultrootwindow)
        eventmask = xlib.InputEventMask.StructureNotify | xlib.InputEventMask.SubstructureRedirect | xlib.InputEventMask.SubstructureNotify
        self.display.install(self.root, eventmask)
        # We are now the window manager - continue install.
        self._importwindows()
        self._managewindows()
        log.debug('0x%08x: root %s', self.root.window, self.root)
        # XXX Should we remove WM_ICON_SIZE from root? In case an old WM installed it. See ICCCM 4.1.9
        def xerrorhandler(display, xerrorevent):
            log.error('X Error: %s', xerrorevent)
            return 0
        self.display.errorhandler = xerrorhandler
        self._make_handlers()
        self.ewmh = ewmh.EwmhWM(self.display, self.root)
        self.ewmh.clientlist = self.clientlist
        self.ewmh.clientliststacking = self.stacklist
        self.show()

    @property
    def clientlist(self):
        """ Client list of windows in creation order. """
        return [window for windowid, window in self.root.children.items() if window in self.stacklist]

    def _importwindows(self):
        """ Import windows into stacklist that look like they'll need to be managed. """
        self.stacklist = [w for w in self.root.children.values() if managewindowp(w)]
        for window in self.stacklist:
            log.debug('0x%08x: importing window %s', window.window, window)

    def _managewindows(self):
        """ Manage imported windows. """
        for window in self.stacklist:
            window.manage(xlib.InputEventMask.StructureNotify)

    def _make_handlers(self):
        self.eventhandlers = {
                xlib.EventName.ClientMessage:       self.handle_clientmessage,
                xlib.EventName.CreateNotify:        self.handle_createnotify,
                xlib.EventName.ConfigureNotify:     self.handle_configurenotify,
                xlib.EventName.ConfigureRequest:    self.handle_configurerequest,
                xlib.EventName.DestroyNotify:       self.handle_destroynotify,
                xlib.EventName.FocusIn:             self.handle_focusin,
                xlib.EventName.FocusOut:            self.handle_focusout,
                xlib.EventName.MapNotify:           self.handle_mapnotify,
                xlib.EventName.MapRequest:          self.handle_maprequest,
                xlib.EventName.UnmapNotify:         self.handle_unmapnotify,
                }

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
            w.resize(self.root.geom)
            w.show()
            self.ewmh.activewindow = w
            log.debug('0x%08x: showing window=%s', w.window, w)
        # Hide every window that's not in the family of windows.
        for w in self.stacklist:
            if w not in family:
                log.debug('0x%08x: hiding %s', w.window, w)
                w.hide()

    def noop(self, event):
        log.debug('noop %s', xlib.EventName(event.type))

    def handle_clientmessage(self, event):
        e = event.xclient
        try:
            msg = self.display.atom[e.message_type]
        except KeyError:
            msg = self.display.getatomname(e.message_type)
        log.debug('0x%08x: handle_clientmessage msgid=%d name=%s', e.window, e.message_type, msg)
        if e.message_type == self.display.atom['_NET_ACTIVE_WINDOW']:
            log.debug('0x%08x: _NET_ACTIVE_WINDOW', e.window)
            try:
                win = self.root.children[e.window]
            except KeyError:
                log.debug('0x%08x: Unknown window, cannot set as active', e.window)
            else:
                self.show(win=win)
        elif e.message_type == self.display.atom['_NET_CLOSE_WINDOW']:
            try:
                win = self.root.children[e.window]
            except KeyError:
                pass
            else:
                win.delete()
                # Do nothing else. We'll receive DestroyNotify etc if the client window is deleted.

    def handle_createnotify(self, event):
        # New window has been created.
        e = event.xcreatewindow
        self.root.newchild(e.window)
        log.debug('0x%08x: CreateNotify parent=0x%08x override_redirect=%s', e.window, e.parent, e.override_redirect)

    def handle_configurenotify(self, event):
        # The X server has moved and/or resized window e.window
        e = event.xconfigure
        # Only handle if the notify event not caused by a sub-structure redirect.
        if e.event == e.window:
            geom = display.Geometry(e)
            log.debug('0x%08x: ConfigureNotify %s', e.window, geom)
            try:
                window = self.root.children[e.window]
            except KeyError:
                pass
            else:
                window.geom = geom
                if window.wantedgeom == geom:
                    log.debug('0x%08x: current dimensions are good, no need to request again', e.window)
                else:
                    # Window is not the size we want, make a configure request.
                    wg = window.wantedgeom
                    log.debug('0x%08x: requesting again, wanted %s current %s', e.window, window.wantedgeom, window.geom)
                    self.display.moveresizewindow(window, wg.x, wg.y, wg.w, wg.h)

    def handle_configurerequest(self, event):
        # Some other client tried to reconfigure e.window
        # NOTE: Allow all configure requests, even if their dimensions are not what we want.
        # Most clients get slow and behave weird if they don't get their way, so we'll honour all
        # requests but we'll request the dimensions we want in the callback configure notify handler.
        e = event.xconfigurerequest
        geom = display.Geometry(e)
        log.debug('0x%08x: ConfigureRequest parent=0x%08x %s %s', e.window, e.parent, geom, e.value_mask)
        wc = xlib.XWindowChanges()
        changemask = 0
        if e.value_mask.value & e.value_mask.CWX:
            changemask |= e.value_mask.CWX
            wc.x = e.x
        if e.value_mask.value & e.value_mask.CWY:
            changemask |= e.value_mask.CWY
            wc.y = e.y
        if e.value_mask.value & e.value_mask.CWWidth:
            changemask |= e.value_mask.CWWidth
            wc.width = e.width
        if e.value_mask.value & e.value_mask.CWHeight:
            changemask |= e.value_mask.CWHeight
            wc.height = e.height
        # Grant requested geom.
        requestedgeom = display.Geometry(wc)
        log.debug('0x%08x: requested %s %s', e.window, xlib.ConfigureWindowStructure(changemask), requestedgeom)
        if changemask:
            self.display.configurewindow(e.window, changemask, wc)

    def handle_destroynotify(self, event):
        # Window has been destroyed.
        e = event.xdestroywindow
        # Only handle if the notify event not caused by a sub-structure redirect.
        if e.event == e.window:
            log.debug('0x%08x: DestroyNotify event=0x%08x', e.window, e.event)
            try:
                self._removewindow(self.root.children[e.window])
            except KeyError:
                log.debug('0x%08x: not found in root %s', e.window, self.root)
            self.show()

    def handle_focusin(self, event):
        e = event.xfocus
        log.debug('0x%08x: focusin mode=%s detail=%s', e.window, e.mode, e.detail)

    def handle_focusout(self, event):
        e = event.xfocus
        log.debug('0x%08x: focusout mode=%s detail=%s', e.window, e.mode, e.detail)

    def handle_mapnotify(self, event):
        # Server has displayed the window.
        e = event.xmap
        # Only handle if the notify event not caused by a sub-structure redirect.
        if e.event == e.window:
            log.debug('0x%08x: MapNotify event=0x%08x override_redirect=%s', e.window, e.event, e.override_redirect)
            # Add a WM_STATE property to the window. See ICCCM 4.1.3.1
            try:
                window = self.root.children[e.window]
            except KeyError:
                log.error('0x%08x: window not found, cannot set WM_STATE=Normal', e.window)
            else:
                if window in self.stacklist:
                    window.wm_state = xlib.WmStateState.Normal

    def handle_maprequest(self, event):
        # A window has requested that it be shown.
        windowid = event.xmaprequest.window
        try:
            win = self.root.children[windowid]
        except KeyError:
            log.error('0x%08x: MapRequest for unknown window!!!', w)
        else:
            if not win.override_redirect:
                # Put window to the top of the list and update display.
                if win not in self.stacklist:
                    i = 0
                    self.stacklist.insert(i, win)
                win.manage(xlib.InputEventMask.EnterWindow | xlib.InputEventMask.FocusChange | xlib.InputEventMask.StructureNotify)
                self.show(win=win)
                self.ewmh.clientlist = self.clientlist
                self.ewmh.clientliststacking = self.stacklist

    def handle_unmapnotify(self, event):
        e = event.xunmap
        if e.send_event:
            # The UnmapNotify is because client called something like XWithdrawWindow or XIconifyWindow.
            # Unmap the window, but remove when the xserver sends another UnmapNotify message with send_event=False.
            log.debug('0x%08x: Client requests unmap.. calling XUnmapWindow', e.window)
            self.display.unmapwindow(e.window)
        else:
            # Only handle if the notify event not caused by a sub-structure redirect. See man XUnmapEvent
            if e.event == e.window and e.window in self.stacklist:
                # X has unmapped the window, we can now put it in the withdrawn state.
                try:
                    win = self.root.children[e.window]
                except KeyError:
                    log.error('0x%08x: UnmapRequest for unknown window!!!', e.window)
                else:
                    # Mark window Withdrawn. See ICCCM 4.1.3.1
                    win.wm_state = xlib.WmStateState.Withdrawn
                    log.debug('0x%08x: Unmap successful %s', e.window, win)
                    # Since the window has been unmapped(hidden) show the next window in the list.
                self.show()

    def _removewindow(self, win):
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

    def __del__(self):
        self.display = None

def managewindowp(window):
    """ manage-window-predicate. Return True if the window should be managed, False otherwise. """
    # Never manage cases where override_redirect=True.
    # We have two extra restrictions when importing windows at program startup.
    # Allow import of windows that have MapState=IsViewable, or WM_STATE exists.
    # This is because X has an extra restriction about windows to manage. ie, X apps can create children of the
    # root window, with their override_redirect=False but never Map them and the window manager then has to ignore them.
    # With these checks we're assuming that IsViewable means the window will want to Map itself or that a prior window
    # manager decided to manage the window and added a WM_STATE attribute so we'll manage it too.
    if window.map_state == xlib.MapState.IsViewable:
        manage = True
    elif window.wm_state:
        manage = True
    elif window.override_redirect:
        manage = False
    else:
        manage = False
    return manage

def parseargs():
    import argparse
    parser = argparse.ArgumentParser()
    footwm.log.addargs(parser)
    args = parser.parse_args()
    footwm.log.configlogging(args.logspec, args.outfile)

def main():
    parseargs()
    try:
        foot = Foot()
    except Exception as e:
        log.exception(e)
    else:
        xevent.run(foot.display, foot.eventhandlers)
