"""
Display module for footwm.

Display abstracts away most of the direct access to the xlib library.

Copyright (c) 2016 Jerry Kotland.
"""

from . import xlib

class DisplayError(Exception):
    """ Error connecting to or managing the display. """
    pass

class Display:

    def __init__(self, displayname=None):
        self.displayname = displayname
        #self._errorhandler = None
        # xh = X handle.
        self.xh = xlib.xlib.XOpenDisplay(displayname)
        if self.xh is None:
            raise DisplayError('Failed to connect to display {}'.format(displayname))

    @property
    def errorhandler(self):
        return self._errorhandler

    @errorhandler.setter
    def errorhandler(self, newhandler):
        # The errorhandler property will store/return the provided newhandler callable.
        self._errorhandler = newhandler
        # Wrap an x error handler func and strip away ctypes specific info before calling.
        def errorfunc(displayp, eventp):
            return newhandler(self, eventp.contents)
        # Need to keep a reference to xerrorhandler_p object to stop it being gc'd.
        self._errorhandlerp = xlib.xerrorhandler_p(errorfunc)
        xlib.xlib.XSetErrorHandler(self._errorhandlerp)

    def install(self, root, eventmask):
        """ Install ourselves as *the* window manager. """
        def installerror(display, xerrorevent):
            # Only one window can watch SubstructureRedirect on the root window so X will set BadAccess if there's another wm running.
            if xerrorevent.error_code == xlib.Error.BadAccess:
                self.installed = False
            # Need to return an int here - it's ignored, but no explicit return will cause an error.
            return 0
        # Assume we're installed, installerror will set to False if the install fails.
        self.installed = True
        self.errorhandler = installerror
        root.manage(eventmask)
        self.sync()
        if not self.installed:
            raise DisplayError('Another WM is running')

    def sync(self, discard=False):
        xlib.xlib.XSync(self.xh, discard)

    def __str__(self):
        return 'Display({})'.format(self.displayname)
