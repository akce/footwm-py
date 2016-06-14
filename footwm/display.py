"""
Display module for footwm.

Display abstracts away most of the direct access to the xlib library.

Copyright (c) 2016 Akce
"""
import ctypes

from . import keydefs
from . import xlib

# addr = address-of, this is a handy shortcut for using ctypes.
addr = ctypes.byref

class DisplayError(Exception):
    """ Error connecting to or managing the display. """
    pass

class Array:
    """ Abstract away x, y access to a linear list. """

    def __init__(self, lst, xwidth):
        self.lst = lst
        self.xwidth = xwidth

    def __call__(self, x, y):
        offset = y * self.xwidth + x
        return self.lst[offset]

class KeySym:

    def __init__(self, keysymid):
        self.keysymid = keysymid
        self.name = keydefs.keysymnames.get(self.keysymid, '???')

    def __hash__(self):
        return hash(self.keysymid)

    def __eq__(self, other):
        return self.keysymid == other.keysymid

    def __str__(self):
        return '{}:0x{:x}'.format(self.name, self.keysymid)

    def __repr__(self):
        """ pprint uses repr to print, so make this nice for our text output. """
        return str(self)

class Display:

    def __init__(self, displayname=None):
        self.displayname = displayname
        #self._errorhandler = None
        # xh = X handle.
        self.xh = xlib.xlib.XOpenDisplay(displayname)
        if self.xh is None:
            raise DisplayError('Failed to connect to display {}'.format(displayname))
        self.atom = {}
        self._nextevent = xlib.XEvent()

    def add_atom(self, symbol, only_if_exists=False):
        self.atom[symbol] = xlib.xlib.XInternAtom(self.xh, bytes(symbol, 'utf8'), only_if_exists)

    @property
    def defaultrootwindow(self):
        return xlib.xlib.XDefaultRootWindow(self.xh)

    @property
    def displaykeycodes(self):
        kmin = ctypes.c_int()
        kmax = ctypes.c_int()
        xlib.xlib.XDisplayKeycodes(self.xh, addr(kmin), addr(kmax))
        return kmin.value, kmax.value

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

    def free(self, xobject):
        xlib.xlib.XFree(xobject)

    def getkeyboardmapping(self, keymin, keycount):
        keysyms_per_keycode = ctypes.c_int()
        kbmapping = xlib.xlib.XGetKeyboardMapping(self.xh, keymin, keycount, ctypes.byref(keysyms_per_keycode))
        #print('keysyms/keycode={}'.format(keysyms_per_keycode.value))
        kbarray = Array(kbmapping, keysyms_per_keycode.value)
        # Convert to non-ctypes.
        # dict(keycode=[KeySym])
        ret = dict([(y + keymin, [KeySym(kbarray(x, y)) for x in range(kbarray.xwidth)]) for y in range(keycount)])
        self.free(kbmapping)
        return ret

    def gettransientfor(self, windowid):
        """ Is the window a transient (eg, a modal dialog box for another window?).
        If it is, return that window's xwindow id. """
        tf = xlib.Window()
        tstatus = xlib.xlib.XGetTransientForHint(self.xh, windowid, addr(tf))
        if tstatus > 0:
            # window is transient, transientfor will contain the window id of the parent window.
            transientfor = tf.value
        else:
            transientfor = None
        return transientfor

    @property
    def keymodifiercodes(self):
        xmodmap = xlib.xlib.XGetModifierMapping(self.xh)
        keypermod = xmodmap.contents.max_keypermod
        modnames = [n for n, _ in xlib.KeyModifierMask._bits_]
        #print('xmodmap.max_keypermod={} modnames={}'.format(keypermod, modnames))
        modarray = Array(xmodmap.contents.modifiermap, keypermod)
        ret = dict([(modnames[y], [modarray(x, y) for x in range(keypermod)]) for y in range(len(modnames))])
        self.free(xmodmap)
        return ret

    def grabkey(self, keycode, modifiermask, grabwindow, ownerevents, pointermode, keyboardmode):
        xlib.xlib.XGrabKey(self.xh, keycode, modifiermask, grabwindow.window, ownerevents, pointermode, keyboardmode)

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

    @property
    def nextevent(self):
        xlib.xlib.XNextEvent(self.xh, addr(self._nextevent))
        return self._nextevent

    def sendevent(self, window, event, eventtype=xlib.InputEventMask.NoEvent):
        """ Do the fancy ctypes event casting before calling XSendEvent. """
        status = xlib.xlib.XSendEvent(self.xh, window.window, False, eventtype, ctypes.cast(ctypes.byref(event), xlib.xevent_p))
        return status != 0

    def sync(self, discard=False):
        xlib.xlib.XSync(self.xh, discard)

    def ungrabkey(self, keycode, modifiermask, grabwindow):
        xlib.xlib.XUngrabKey(self.xh, keycode, modifiermask, grabwindow.window)

    def unmapwindow(self, window):
        # XXX window must be an actual windowid for now. There may still be cases where we need to unmap a window with no associated object.
        xlib.xlib.XUnmapWindow(self.xh, window)

    def __del__(self):
        xlib.xlib.XCloseDisplay(self.xh)
        self.xh = None

    def __str__(self):
        return 'Display({})'.format(self.displayname)
