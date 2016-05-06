"""
Main footwm module.

Copyright (c) 2016 Akce
"""

# Python standard modules.
import ctypes   # TODO xlib needs to abstract enough so clients don't need ctypes!
import logging
import sys

# Local modules.
import footwm.xlib as xlib
import footwm.log

log = footwm.log.make(handler=logging.FileHandler('debug.log'))

def xerrorhandler(display_p, event_p):
    event = event_p.contents
    log.error('X Error: %s', event)
    return 0

class Foot(object):

    WMEVENTS = xlib.InputEventMask.SubstructureRedirect | xlib.InputEventMask.SubstructureNotify

    def __init__(self, displayname=None):
        # The shown window is always at index 0.
        self.windows = []
        self._atoms = {}
        self.display = xlib.xlib.XOpenDisplay(displayname)
        log.debug('x connect displayname=%s', displayname) #, self.display.contents)
        self._init_atoms()
        self._install_wm()
        # TODO Lock the X server and import all existing windows?
        self._import_windows()
        self._make_handlers()

    def _init_atoms(self):
        def aa(symbol, only_if_exists=False):
            self._atoms[symbol] = xlib.xlib.XInternAtom(self.display, symbol, only_if_exists)
        aa(b'WM_STATE')

    def _make_handlers(self):
        self.eventhandlers = {
                xlib.EventName.MapRequest: self.handle_maprequest,
                xlib.EventName.UnmapNotify: self.handle_unmapnotify,
                }

    def _import_windows(self):
        root_return = xlib.Window(0)
        parent_of_root = xlib.Window(0)
        root = xlib.xlib.XDefaultRootWindow(self.display)
        childrenp = xlib.window_p()
        nchildren = ctypes.c_uint(0)

        status = xlib.xlib.XQueryTree(self.display, root, ctypes.byref(root_return), ctypes.byref(parent_of_root), ctypes.byref(childrenp), ctypes.byref(nchildren))
        # XXX assert that root_return == root?
        log.debug('XQueryTree nchildren=%s', nchildren.value)
        for i in range(nchildren.value):
            self._add_window(childrenp[i])
        if nchildren.value > 0:
            xlib.xlib.XFree(childrenp)
        log.debug('windows %s', self.windows)

    def _get_wm_state(self, window):
        state = None
        # TODO move this into a window object @property.
        a = ctypes.byref        # a = address shorthand.
        WM_STATE = self._atoms[b'WM_STATE']
        actual_type_return = xlib.Atom()
        actual_format_return = ctypes.c_int()
        nitems_return = ctypes.c_ulong(0)
        bytes_after_return = ctypes.c_ulong()
        prop_return = xlib.byte_p()
        # sizeof return WmState struct in length of longs, not bytes. See XGetWindowProperty
        long_length = int(ctypes.sizeof(xlib.WmState) / ctypes.sizeof(ctypes.c_long))

        ret = xlib.xlib.XGetWindowProperty(self.display, window, WM_STATE, 0, long_length, False, WM_STATE, a(actual_type_return), a(actual_format_return), a(nitems_return), a(bytes_after_return), a(prop_return))
        if ret == 0:
            # Success! We need also check if anything was returned..
            if nitems_return.value > 0:
                # Cast the prop_return to a *WmState and return.
                state = xlib.WmState()
                sp = ctypes.cast(prop_return, xlib.wmstate_p).contents
                state.state = sp.state
                state.icon = sp.icon
            xlib.xlib.XFree(prop_return)
        return state

    def _set_wm_state(self, window, winstate):
        state = xlib.WmState()
        #state.state = xlib.WmStateState(state)
        state.state = xlib.WmStateState(winstate)
        state.icon = 0
        WM_STATE = self._atoms[b'WM_STATE']
        data_p = ctypes.cast(ctypes.byref(state), xlib.byte_p)
        long_length = int(ctypes.sizeof(state) / ctypes.sizeof(ctypes.c_long))
        # Specify as 32 (longs), that way the Xlib client will handle endian translations.
        xlib.xlib.XChangeProperty(self.display, window, WM_STATE, WM_STATE, 32, xlib.PropMode.Replace, data_p, long_length)

    def _add_window(self, window):
        log.debug('_add_window %s', window)
        wa = xlib.XWindowAttributes()
        astatus = xlib.xlib.XGetWindowAttributes(self.display, window, ctypes.byref(wa))
        if astatus > 0:
            # XGetWindowAttr completed successfully.
            if wa.override_redirect:
                log.debug('  ignore window - override_redirect is True')
            else:
                log.debug('xwinattr x=%s y=%s w=%s h=%s mapstate=%s my=%s', wa.x, wa.y, wa.width, wa.height, wa.map_state, wa.your_event_mask)
                # Is the window a transient (eg, a modal dialog box for another window?)
                # TODO see how multiple windows are done for apps like gimp.
                # TODO maybe WM_HINTS:WindowGroupHint
                # XXX Can we have a transient with no parent?
                transientfor = xlib.Window()
                tstatus = xlib.xlib.XGetTransientForHint(self.display, window, ctypes.byref(transientfor))
                if tstatus > 0:
                    # window is transient, transientfor will contain the window id of the parent window.
                    log.debug('xtransient ret=%s for=%s', tstatus, transientfor.value)
                    # TODO do something with transientfor.
                else:
                    # Add and manage the window.
                    # All normal windows are kept in the withdrawn state unless they're on the top of the MRU stack.
                    self.windows.append(window)
                    if wa.map_state != xlib.MapState.IsUnmapped:
                        xlib.xlib.XUnmapWindow(self.display, window)
                    # Add a WM_STATE property to the window. See ICCCM 4.1.3.1
                    self._set_wm_state(window, xlib.WmStateState.Withdrawn)
        else:
            log.error('XGetWindowAttributes failed! window=%s', window)

    def _install_wm(self):
        """ Install foot as *the* window manager. """
        # Assume we can install, wmerrhandler will tell us if we can't be the window manager.
        installed = True
        def wmerrhandler(display_p, event_p):
            nonlocal installed
            # XSelectInput(rootwin) will set BadAccess if there's another wm running.
            if event_p.contents.error_code == xlib.Error.BadAccess:
                installed = False
            # Need to return an int here - it's ignored. No explicit return will cause an error.
            return 0
        root = xlib.xlib.XDefaultRootWindow(self.display)
        olderrorhandler = xlib.XSetErrorHandler(wmerrhandler)
        xlib.xlib.XSelectInput(self.display, root, self.WMEVENTS)
        xlib.xlib.XSync(self.display, False)
        if installed:
            # We are now the window manager - continue install.
            # XXX Should we remove WM_ICON_SIZE from root? In case an old WM installed it. See ICCCM 4.1.9
            # Install regular X error handler.
            xlib.XSetErrorHandler(xerrorhandler)
        else:
            # Exit.
            log.error('Another WM is already running!')
            sys.exit(1)

    def run(self):
        event = xlib.XEvent()
        while True:
            xlib.xlib.XNextEvent(self.display, ctypes.byref(event))
            e = xlib.EventName(event.type)
            log.debug('event: %s', e)
            try:
                handler = self.eventhandlers[e.value]
            except KeyError:
                log.error('unhandled event %s', xlib.EventName(event.type))
            else:
                handler(event)

    def noop(self, event):
        log.debug('noop %s', xlib.EventName(event.type))

    def handle_maprequest(self, event):
        w = event.xmaprequest.window
        log.debug('MapRequest window=%s known=%s', w, w in self.windows)
        xlib.xlib.XMapWindow(self.display, w)

    def handle_unmapnotify(self, event):
        # TODO handle xunmap.event != xunmap.window / xunmap.from_configure cases. See man XUnmapEvent
        if event.xunmap.send_event:
            # The UnmapNotify is because client called something like XWithdrawWindow or XIconifyWindow.
            xlib.xlib.XUnmapWindow(self.display, event.xunmap.window)
        else:
            # X has unmapped the window, we can now put it in the withdrawn state.
            self._set_wm_state(event.xunmap.window, xlib.WmStateState.Withdrawn)
            # TODO now draw next priority window?

    def __del__(self):
        xlib.xlib.XCloseDisplay(self.display)
        self.display = None

def main():
    try:
        foot = Foot()
    except Exception as e:
        log.exception(e)
    foot.run()
