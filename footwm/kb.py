"""
Keyboard module for footwm.

Copyright (c) 2016 Jerry Kotland
"""
import ctypes

from . import keydefs
from . import xlib

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

    def __str__(self):
        name = keydefs.keysymnames.get(self.keysymid, '???')
        return '{}:0x{:x}'.format(name, self.keysymid)

    def __repr__(self):
        """ pprint uses repr to print, so make this nice for our text output. """
        return str(self)

class Keyboard:

    def __init__(self, display):
        self.display = display
        self._load_keysymgroups()
        self._load_keymodifiercodes()
        self._load_keymodifiersyms()

    def _load_keysymgroups(self):
        """ List of keycodes and their keysym groups. """
        kmin = ctypes.c_int()
        kmax = ctypes.c_int()

        xlib.xlib.XDisplayKeycodes(self.display, ctypes.byref(kmin), ctypes.byref(kmax))
        kcount = kmax.value - kmin.value
        #print('keycode min={} max={} count={}'.format(kmin.value, kmax.value, kcount))
        keysyms_per_keycode = ctypes.c_int()
        kbmapping = xlib.xlib.XGetKeyboardMapping(self.display, kmin.value, kcount, ctypes.byref(keysyms_per_keycode))
        #print('keysyms/keycode={}'.format(keysyms_per_keycode.value))
        kbarray = Array(kbmapping, keysyms_per_keycode.value)
        # Convert to non-ctypes.
        # dict(keycode=[KeySym])
        self.keysymgroups = dict([(y + kmin.value, [KeySym(kbarray(x, y)) for x in range(kbarray.xwidth)]) for y in range(kcount)])
        xlib.xlib.XFree(kbmapping)

    def _load_keymodifiercodes(self):
        """ List of key modifier masks and their keycodes. """
        xmodmap = xlib.xlib.XGetModifierMapping(self.display)
        keypermod = xmodmap.contents.max_keypermod
        modnames = [n for n, _ in xlib.KeyModifierMask._bits_]
        #print('xmodmap.max_keypermod={} modnames={}'.format(keypermod, modnames))
        modarray = Array(xmodmap.contents.modifiermap, keypermod)
        self.keymodifiercodes = dict([(modnames[y], [modarray(x, y) for x in range(keypermod)]) for y in range(len(modnames))])
        xlib.xlib.XFree(xmodmap)

    def _load_keymodifiersyms(self):
        """ Keymodifier map has modifiers mapped to keysym groups. """
        self.keymodifiersyms = dict([(modname, [self.keysymgroups.get(k, None) for k in kcodes]) for modname, kcodes in self.keymodifiercodes.items()])
