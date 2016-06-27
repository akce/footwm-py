"""
FootKeys module.

Copyright (c) 2016 Akce
"""

from . import clientcmd
from . import display
from . import ewmh
from . import log as logger
from . import kb
from . import window
from . import xevent
from . import xlib

log = logger.make(name=__name__)

class FootKeys:

    def __init__(self, displayname=None):
        self.display = display.Display(displayname)
        log.debug('%s: connect display=%s', self.__class__.__name__, self.display)
        self.root = window.RootWindow(self.display, self.display.defaultrootwindow)
        self.ewmh = ewmh.EwmhClient(self.display, self.root)
        self.keyboard = kb.Keyboard(self.display)
        activateargs = self, self.display, self.root, self.ewmh, clientcmd.activatewindow
        closeargs = self, self.display, self.root, self.ewmh, clientcmd.closewindow
        self.keymap = {
                'F5': clientcmd.ClientCommand(*activateargs, index=1),
                'F6': clientcmd.ClientCommand(*activateargs, index=2),
                'F7': clientcmd.ClientCommand(*activateargs, index=3),
                'F8': clientcmd.ClientCommand(*activateargs, index=4),
                'F9': clientcmd.ClientCommand(*closeargs, index=0),
                }
        self.clearkeymap()
        self._installkeymap()
        self._makehandlers()

    def clearkeymap(self):
        self.display.ungrabkey(xlib.AnyKey, xlib.GrabKeyModifierMask.AnyModifier, self.root)

    def _installkeymap(self):
        """ Installs the window manager top level keymap to selected windows. Install to all managed windows if windows is None. """
        self.root.manage(xlib.InputEventMask.KeyPress)
        for keysymname in self.keymap:
            # TODO handle locked modifiers scroll-lock, num-lock, caps-lock.
            keycode, modifier = self.keyboard.keycodes[keysymname]
            self.display.grabkey(keycode, modifier, self.root, True, xlib.GrabMode.Async, xlib.GrabMode.Async)
            log.debug('0x%08x: install keygrab keycode=0x%x modifier=0x%x', self.root.window, keycode, modifier)

    def _makehandlers(self):
        self.eventhandlers = {
                xlib.EventName.KeyPress:            self.handle_keypress,
                xlib.EventName.MappingNotify:       self.handle_mappingnotify,
                }

    def handle_keypress(self, event):
        """ User has pressed a key that we've grabbed. """
        e = event.xkey
        log.debug('0x%08x: handle_keypress keycode=0x%x modifiers=%s', e.window, e.keycode, e.state)
        # Convert keycode to keysym and call the associated handler.
        # TODO handle locked modifiers scroll-lock, num-lock, caps-lock.
        try:
            keysym = self.keyboard.keysyms[(e.keycode, e.state.value)]
        except KeyError:
            log.error('0x%08x: no keysym for (keycode, modifier)', e.window)
        else:
            try:
                keyfunc = self.keymap[keysym]
            except KeyError:
                log.error('0x%08x: no function for keysym=%s', e.window, keysym)
            else:
                keyargs = (self, self.root, keysym, e.keycode, e.state.value)
                keyfunc(keyargs=keyargs)

    def handle_mappingnotify(self, event):
        """ X server has had a keyboard mapping changed. Update our keyboard layer. """
        self.clearkeymap()
        # Recreate keyboard settings.
        self.keyboard = kb.Keyboard(self.display)
        self._installkeymap()

def logkey(keyargs):
    app, win, keysym, keycode, modifiers = keyargs
    log.debug('0x%08x: logkey keysym=%s keycode=%d modifiers=0x%x', win.window, keysym, keycode, modifiers)

def main():
    fk = FootKeys()
    xevent.run(fk.display, fk.eventhandlers)
    fk.clearkeymap()
