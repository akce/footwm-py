"""
Keyboard module for footwm.

Copyright (c) 2016 Akce
"""
from . import xlib

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
        kmin, kmax = self.display.displaykeycodes
        kcount = kmax - kmin
        #print('keycode min={} max={} count={}'.format(kmin, kmax, kcount))
        self.keysymgroups = self.display.getkeyboardmapping(kmin, kcount)

    def _load_keymodifiercodes(self):
        """ List of key modifier masks and their keycodes. """
        self.keymodifiercodes = self.display.keymodifiercodes

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
