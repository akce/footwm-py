"""
EWMH support for footwm.

Implements only those parts relevant for footwm.

See:
    https://specifications.freedesktop.org/wm-spec/wm-spec-latest.html

Copyright (c) 2016 Akce
"""

ewmh_major = 1
ewmh_minor = 5
ewmh_version = (ewmh_major, ewmh_minor)

import ctypes

from . import xlib

class Ewmh:

    def __init__(self, display, root):
        """ Initialise EWMH support. """
        self.display = display
        self.root = root
        self._initatoms()
        self._initsupportingwmcheck()

    def _initatoms(self):
        """ Initialise the EWMH atoms we support. """
        ## Initialise EWMH ATOMs.
        supported = [
                # Supported EWMH atoms.
                '_NET_ACTIVE_WINDOW',
                '_NET_CLIENT_LIST_STACKING',
                '_NET_CLOSE_WINDOW',
                '_NET_SUPPORTING_WM_CHECK',
                '_NET_WM_FULL_PLACEMENT',
                '_NET_WM_NAME',
                ]
        self.display.add_atom('_NET_SUPPORTED')
        # UTF8 data type.
        self.display.add_atom('UTF8_STRING')
        for s in supported:
            self.display.add_atom(s)
        ls = len(supported)
        csupported = (ctypes.c_ulong * ls)()
        for i, s in enumerate(supported):
            csupported[i] = self.display.atom[s]
        # TODO see if I can nicely push the ctypes stuff into display.
        self.display.changeproperty(self.root, '_NET_SUPPORTED', xlib.XA.ATOM, 32, xlib.PropMode.Replace, ctypes.byref(csupported), ls)

    def _initsupportingwmcheck(self):
        """ _NET_SUPPORTING_WM_CHECK """
        # Create the child window for _NET_SUPPORTING_WM_CHECK.
        self.window = self.display.createsimplewindow(self.root, 0, 0, 1, 1, 0, 0, 0)
        propname = '_NET_SUPPORTING_WM_CHECK'
        cwin = xlib.Window(self.window)
        # Set window id on root window.
        self.display.changeproperty(self.root, propname, xlib.XA.WINDOW, 32, xlib.PropMode.Replace, ctypes.byref(cwin), 1)
        # Set window id on child window.
        self.display.changeproperty(self.window, propname, xlib.XA.WINDOW, 32, xlib.PropMode.Replace, ctypes.byref(cwin), 1)
        # Set window manager name on child window.
        bname = bytes('footwm', 'utf8')
        blen = len(bname)
        cwinname = (ctypes.c_byte * blen)()
        for i, b in enumerate(bname):
            cwinname[i] = b
        self.display.changeproperty(self.window, '_NET_WM_NAME', self.display.atom['UTF8_STRING'], 8, xlib.PropMode.Replace, ctypes.byref(cwinname), blen)

    def clientlist(self, windows):
        """ _NET_CLIENT_LIST """
        self._setwindows(windows, '_NET_CLIENT_LIST')

    def clientliststacking(self, windows):
        """ _NET_CLIENT_LIST_STACKING """
        self._setwindows(windows, '_NET_CLIENT_LIST_STACKING')

    def _setwindows(self, windows, propname):
        lw = len(windows)
        cwindows = (ctypes.c_ulong * lw)()
        for i, w in enumerate(windows):
            cwindows[i] = w.window
        self.display.changeproperty(self.root, propname, xlib.XA.WINDOW, 32, xlib.PropMode.Replace, ctypes.byref(cwindows), lw)

    def activewindow(self, window):
        """ _NET_ACTIVE_WINDOW """
        cwin = xlib.Window(window.window)
        self.display.changeproperty(self.root, '_NET_ACTIVE_WINDOW', xlib.XA.WINDOW, 32, xlib.PropMode.Replace, ctypes.byref(cwin), 1)

    def __del__(self):
        self.display.destroywindow(self.window)
        self.window = None
