#! /usr/bin/env python3
"""
Dump X keyboard keys.

Small script to see how X keycodes & modifiers are all tied together.

Copyright (c) 2016 Jerry Kotland
"""
import ctypes
import pprint

import footwm.kb as kb
import footwm.xlib as xlib

if __name__ == '__main__':
    d = xlib.xlib.XOpenDisplay(None)
    keyboard = kb.Keyboard(d)
    pprint.pprint(keyboard.keysymgroups, width=200)
    pprint.pprint(keyboard.keymodifiercodes, width=200)
    pprint.pprint(keyboard.keymodifiersyms, width=200)
