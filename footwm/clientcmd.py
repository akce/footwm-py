"""
Client window commands.

Copyright (c) 2016 Jerry Kotland
"""

import types

from . import log as logger

log = logger.make(name=__name__)

class ClientCommand:
    """ Client command wrapper object. """
    def __init__(self, app, display, root, ewmh, command, **kwargs):
        self.app = app
        self.display = display
        self.root = root
        self.ewmh = ewmh
        self.command = types.MethodType(command, self)
        self.kwargs = kwargs

    def __call__(self, keyargs):
        self.keyargs = keyargs
        return self.command(**self.kwargs)

def activatewindow(self, index=0):
    """ Send an EWMH _NET_ACTIVE_WINDOW message to the window manager. """
    wins = self.ewmh.clientliststacking
    win = wins[index]
    log.debug("0x%08x: activatewindow index=%d win=%s", win.window, index, win)
    self.ewmh.clientmessage('_NET_ACTIVE_WINDOW', win)

def closewindow(self, index=0):
    """ Send an ICCCM WM_DELETE_WINDOW message to the window. """
    wins = self.ewmh.clientliststacking
    win = wins[index]
    log.debug("0x%08x: closewindow win=%s", win.window, win)
    win.delete()
