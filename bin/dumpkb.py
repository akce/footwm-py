#! /usr/bin/env python3
"""
Dump X keyboard keys.

Small script to see how X keycodes & modifiers are all tied together.

Copyright (c) 2016 Akce
"""
import pprint

import footwm.kb as kb
import footwm.display as display

if __name__ == '__main__':
    d = display.Display()
    keyboard = kb.Keyboard(d)
    print('Keysym groups:')
    pprint.pprint(keyboard.keysymgroups, width=200)
    print('Modifier codes:')
    pprint.pprint(keyboard.keymodifiercodes, width=200)
    print('Modifier keysyms:')
    pprint.pprint(keyboard.keymodifiersyms, width=200)
    print('Keycodes:')
    pprint.pprint(keyboard.keycodes, width=200)
    print('Modifiers:')
    pprint.pprint(keyboard.modifiers, width=200)
