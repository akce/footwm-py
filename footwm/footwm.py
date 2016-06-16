"""
Main footwm module.

Copyright (c) 2016 Akce
"""

# Python standard modules.
import functools
import logging

# Local modules.
import footwm.xlib as xlib
from . import display
from . import ewmh
from . import window as xwin
import footwm.kb as kb
import footwm.log

log = footwm.log.make(handler=logging.FileHandler('debug.log'))
log.addHandler(logging.StreamHandler())

def logkey(keyargs):
    wm, window, keysym, keycode, modifiers = keyargs
    log.debug('0x%08x: logkey keysym=%s keycode=%d modifiers=0x%x', window.window, keysym, keycode, modifiers)


class Foot(object):

    def __init__(self, displayname=None):
        self.display = display.Display(displayname)
        log.debug('%s: connect display=%s', self.__class__.__name__, self.display)
        self.keyboard = kb.Keyboard(self.display)
        self.keymap = {
                'F5': functools.partial(self.show, 1),
                'F6': functools.partial(self.show, 2),
                'F7': functools.partial(self.show, 3),
                'F8': functools.partial(self.show, 4),
                'F9': functools.partial(self.delete_window, 0),
                }
        self._init_atoms()
        # TODO: worry about screens, displays, xrandr and xinerama!
        self.root = xwin.RootWindow(self.display, self.display.defaultrootwindow)
        log.debug('0x%08x: _load_root %s', self.root.window, self.root)
        eventmask = xlib.InputEventMask.StructureNotify | xlib.InputEventMask.SubstructureRedirect | xlib.InputEventMask.SubstructureNotify
        self.display.install(self.root, eventmask)
        # We are now the window manager - continue install.
        # XXX Should we remove WM_ICON_SIZE from root? In case an old WM installed it. See ICCCM 4.1.9
        def xerrorhandler(display, xerrorevent):
            log.error('X Error: %s', xerrorevent)
            return 0
        self.display.errorhandler = xerrorhandler
        self._make_handlers()
        self.install_keymap()
        self.install_keymap(windows=[self.root])
        self.ewmh = ewmh.Ewmh(self.display, self.root)
        self.ewmh.clientliststacking(self.root.children)
        self.show()

    def _init_atoms(self):
        self.display.add_atom('WM_STATE')
        self.display.add_atom('WM_PROTOCOLS')
        self.display.add_atom('WM_DELETE_WINDOW')
        self.display.add_atom('WM_TAKE_FOCUS')

    def clear_keymap(self):
        for w in self.root.children:
            self.display.ungrabkey(xlib.AnyKey, xlib.GrabKeyModifierMask.AnyModifier, w)

    def install_keymap(self, windows=None):
        """ Installs the window manager top level keymap to selected windows. Install to all managed windows if windows is None. """
        if windows is None:
            ws = self.root.children
        else:
            ws = windows
        for keysymname in self.keymap:
            # TODO handle locked modifiers scroll-lock, num-lock, caps-lock.
            keycode, modifier = self.keyboard.keycodes[keysymname]
            # XXX Should we install the keymap only when the window is focused?
            for w in ws:
                self.display.grabkey(keycode, modifier, w, True, xlib.GrabMode.Async, xlib.GrabMode.Async)

    def _make_handlers(self):
        self.eventhandlers = {
                xlib.EventName.ClientMessage:       self.handle_clientmessage,
                xlib.EventName.CreateNotify:        self.handle_createnotify,
                xlib.EventName.ConfigureNotify:     self.handle_configurenotify,
                xlib.EventName.ConfigureRequest:    self.handle_configurerequest,
                xlib.EventName.DestroyNotify:       self.handle_destroynotify,
                xlib.EventName.KeyPress:            self.handle_keypress,
                xlib.EventName.MappingNotify:       self.handle_mappingnotify,
                xlib.EventName.MapNotify:           self.handle_mapnotify,
                xlib.EventName.MapRequest:          self.handle_maprequest,
                xlib.EventName.UnmapNotify:         self.handle_unmapnotify,
                }

    def show(self, index=0, keyargs=None):
        """ Pick a child window to bring to front. Any parents of transient windows will also be shown. """
        try:
            family = self.root.pick(index=index)
        except IndexError:
            log.warning('0x{:08x}: pick index={} out of bounds. children len={}'.format(self.root.window, index, len(self.root.children)))
        else:
            # XXX Only select input on mapped (visible) window(s).
            for window in reversed(family):
                window.resize(self.root.geom)
                window.show()
                log.debug('0x%08x: showing window=%s', window.window, window)
            # Focus the very top window.
            if family:
                self.ewmh.activewindow(window)
                window.focus()
            # Hide every window that's not in the family of windows.
            for window in self.root.children:
                if window not in family:
                    log.debug('0x%08x: hiding %s', window.window, window)
                    window.hide()

    def delete_window(self, index, keyargs=None):
        """ Delete a window. """
        try:
            w = self.root.children[index]
        except IndexError:
            pass
        else:
            w.delete()
            # Do nothing else. We'll receive DestroyNotify etc if the client window is deleted.

    def run(self):
        while True:
            try:
                event = self.display.nextevent
                e = xlib.EventName(event.type)
                #log.debug('event: %s', e)
                try:
                    handler = self.eventhandlers[e.value]
                except KeyError:
                    log.error('unhandled event %s', e)
                else:
                    handler(event)
            except Exception as e:
                log.exception(e)

    def noop(self, event):
        log.debug('noop %s', xlib.EventName(event.type))

    def handle_clientmessage(self, event):
        e = event.xclient
        if e.message_type == self.display.atom['_NET_ACTIVE_WINDOW']:
            window = self.root.find_child(e.window)
            if window:
                self.show(index=self.root.children.index(window))
        elif e.message_type == self.display.atom['_NET_CLOSE_WINDOW']:
            window = self.root.find_child(e.window)
            if window:
                window.delete()

    def handle_createnotify(self, event):
        # New window has been created.
        e = event.xcreatewindow
        geom = xwin.Geometry(e)
        log.debug('0x%08x: CreateNotify parent=0x%08x %s override_redirect=%s', e.window, e.parent, geom, e.override_redirect)

    def handle_configurenotify(self, event):
        # The X server has moved and/or resized window e.window
        e = event.xconfigure
        # Only handle if the notify event not caused by a sub-structure redirect.
        if e.event == e.window:
            geom = xwin.Geometry(e)
            log.debug('0x%08x: ConfigureNotify %s', e.window, geom)
            window = self.root.find_child(e.window)
            if window:
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
        geom = xwin.Geometry(e)
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
        requestedgeom = xwin.Geometry(wc)
        log.debug('0x%08x: requested %s %s', e.window, xlib.ConfigureWindowStructure(changemask), requestedgeom)
        self.display.configurewindow(e.window, changemask, wc)

    def handle_destroynotify(self, event):
        # Window has been destroyed.
        e = event.xdestroywindow
        # Only handle if the notify event not caused by a sub-structure redirect.
        if e.event == e.window:
            log.debug('0x%08x: DestroyNotify event=0x%08x', e.window, e.event)
            # Remove the destroyed window from window hierarchy.
            w = self.root.find_child(e.window)
            if w is None:
                log.debug('0x%08x: not found in root %s', e.window, self.root)
            else:
                self.root.remove_child(w)
                self.ewmh.clientliststacking(self.root.children)
                log.debug('0x%08x: removed from root 0x%08x', w.window, self.root.window)
            self.show()

    def handle_keypress(self, event):
        """ User has pressed a key that we've grabbed. """
        e = event.xkey
        log.debug('0x%08x: handle_keypress keycode=0x%x modifiers=%s', e.window, e.keycode, e.state)
        # Convert keycode to keysym and call the associated handler.
        # TODO handle locked modifiers scroll-lock, num-lock, caps-lock.
        try:
            keysym = self.keyboard.keysyms[(e.keycode, e.state.value)]
        except KeyError:
            log.error('0x%08x: no keysym for (keycode, modifier)', e.window)
        else:
            try:
                keyfunc = self.keymap[keysym]
            except KeyError:
                log.error('0x%08x: no function for keysym=%s', e.window, keysym)
            else:
                keyargs = (self, self.root.find_child(e.window), keysym, e.keycode, e.state.value)
                keyfunc(keyargs=keyargs)

    def handle_mappingnotify(self, event):
        """ X server has had a keyboard mapping changed. Update our keyboard layer. """
        self.clear_keymap()
        # Recreate keyboard settings.
        self.keyboard = kb.Keyboard(self.display)
        self.install_keymap()

    def handle_mapnotify(self, event):
        # Server has displayed the window.
        e = event.xmap
        # Only handle if the notify event not caused by a sub-structure redirect.
        if e.event == e.window:
            log.debug('0x%08x: MapNotify event=0x%08x override_redirect=%s', e.window, e.event, e.override_redirect)
            # Add a WM_STATE property to the window. See ICCCM 4.1.3.1
            window = self.root.find_child(e.window)
            if window:
                window.wm_state = xlib.WmStateState.Normal
            else:
                log.error('0x%08x: window not found, cannot set WM_STATE=Normal', e.window)

    def handle_maprequest(self, event):
        # A window has requested that it be shown.
        w = event.xmaprequest.window
        window = self.root.find_child(w)
        log.debug('0x%08x: MapRequest known=%s', w, window is not None)
        if window is None:
            p = event.xmaprequest.parent
            window = self.root.add_child(w)
            if window:
                self.install_keymap(windows=[window])
        if window:
            # Put window to the top of the list.
            self.show(index=self.root.children.index(window))
            self.ewmh.clientliststacking(self.root.children)

    def handle_unmapnotify(self, event):
        e = event.xunmap
        if e.send_event:
            # The UnmapNotify is because client called something like XWithdrawWindow or XIconifyWindow.
            # Unmap the window, but remove when the xserver sends another UnmapNotify message with send_event=False.
            log.debug('0x%08x: Client requests unmap.. calling XUnmapWindow', e.window)
            self.display.unmapwindow(e.window)
        else:
            # Only handle if the notify event not caused by a sub-structure redirect. See man XUnmapEvent
            if e.event == e.window:
                # X has unmapped the window, we can now put it in the withdrawn state.
                window = self.root.find_child(e.window)
                if window:
                    # Mark window Withdrawn. See ICCCM 4.1.3.1
                    window.wm_state = xlib.WmStateState.Withdrawn
                    log.debug('0x%08x: Unmap successful %s', e.window, window)
                    # Since the window has been unmapped(hidden) show the next window in the list.
                self.show()

    def __del__(self):
        self.display = None

def main():
    try:
        foot = Foot()
    except Exception as e:
        log.exception(e)
    else:
        foot.run()
