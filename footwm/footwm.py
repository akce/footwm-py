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

class Foot(object):

    WMEVENTS = xlib.InputEventMask.SubstructureRedirect | xlib.InputEventMask.SubstructureNotify

    def __init__(self, displayname=None):
        self.display = xlib.xlib.XOpenDisplay(displayname)
        log.debug('x connect displayname=%s', displayname) #, self.display.contents)
        self._make_handlers()
        self._install_wm()
        # TODO Lock the X server and import all existing windows?
        # self._import_windows()

    def _make_handlers(self):
        self.eventhandlers = {
                xlib.EventName.MapRequest: self.handle_maprequest,
                }

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
            # TODO Install regular X error handler.
            pass
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
                log.error('unhandled event %s', e)
            else:
                handler(event)

    def handle_maprequest(self, event):
        log.debug('MapRequest event')
        xlib.xlib.XMapWindow(self.display, event.xmaprequest.window)

    def __del__(self):
        xlib.xlib.XCloseDisplay(self.display)
        self.display = None

def main():
    foot = Foot()
    foot.run()
