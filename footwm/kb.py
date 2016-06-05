"""
Keyboard module for footwm.

Copyright (c) 2016 Akce
"""
import ctypes
import itertools

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

class Keyboard:

    def __init__(self, display):
        self.display = display
        self._load_keysymgroups()
        self._load_keymodifiercodes()
        self._load_keymodifiersyms()
        self._load_modifiers()
        self._load_keycodes()
        self._load_keysyms()

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

    def _keycodes(self):
        """ Return keysym -> keycode, modifier. raise AttributeError if unknown. """
        for keycode, keysyms in self.keysymgroups.items():
            keya = keysyms[0]
            keyb = keysyms[1]
            if keyb.keysymid == xlib.NoSymbol:
                # keyb is the same as keya.
                realkeyb = keya
            else:
                realkeyb = keyb
            yield keya, (keycode, 0)
            if keya != realkeyb:
                if realkeyb.name.startswith('KP_'):
                    modifier = self.modifiers['NumLock']
                else:
                    modifier = self.modifiers['ShiftLock']
                yield realkeyb, (keycode, modifier)

    def _load_keycodes(self):
        """ Creates a dict(keysym: (keycode, modifiermask)) """
        self.keycodes = {keysym.name: keymod for keysym, keymod in self._keycodes()}

    def _load_keysyms(self):
        """ Creates a dict((keycode, modifiermask): keysym) """
        self.keysyms = {v: k for k, v in self.keycodes.items()}

    def _load_modifiers(self):
        self.modifiers = {'ShiftLock': xlib.KeyModifierMask.Shift}
        for modname, keygroups in self.keymodifiersyms.items():
            for keygroup in keygroups:
                # Look in only the first two keys. ie, we don't support mode-switch.
                try:
                    for keysym in keygroup[:2]:
                        if keysym.name in ['Alt_L', 'Alt_R', 'Meta_L', 'Meta_R']:
                            self.modifiers['Alt'] = getattr(xlib.KeyModifierMask, modname)
                        elif keysym.name in ['Super_L', 'Super_R']:
                            self.modifiers['Super'] = getattr(xlib.KeyModifierMask, modname)
                        elif keysym.name == 'Num_Lock':
                            self.modifiers['NumLock'] = getattr(xlib.KeyModifierMask, modname)
                        elif keysym.name == 'Scroll_Lock':
                            self.modifiers['ScrollLock'] = getattr(xlib.KeyModifierMask, modname)
                except TypeError:
                    pass
