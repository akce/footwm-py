"""
Client window commands.

Copyright (c) 2016 Akce
"""

import types

from . import command
from . import display
from . import ewmh
from . import log as logger
from . import window

log = logger.make(name=__name__)

class ClientCommand:
    """ X client commands. """
    def __init__(self, display, root, ewmh, command):
        self.display = display
        self.root = root
        self.ewmh = ewmh
        self.command = command

    def activatewindow(self, stacking=True, index=None, window=None):
        """ Send an EWMH _NET_ACTIVE_WINDOW message to the window manager. """
        win = self._getwindow(stacking=stacking, index=index, window=window)
        if win:
            log.debug("0x%08x: activatewindow index=%s win=%s", win.window, index, win)
            self.ewmh.clientmessage('_NET_ACTIVE_WINDOW', win)

    def closewindow(self, stacking=True, index=None, window=None):
        """ Send an ICCCM WM_DELETE_WINDOW message to the window. """
        win = self._getwindow(stacking=stacking, index=index, window=window)
        if win:
            log.debug("0x%08x: closewindow index=%s win=%s", win.window, index, win)
            win.delete()

    def adddesktop(self, name, index):
        self.command.adddesktop(name, index)

    def deletedesktop(self, index):
        self.command.deletedesktop(index)

    def renamedesktop(self, index, name):
        self.command.renamedesktop(index, name)

    def selectdesktop(self, index):
        self.command.selectdesktop(index)

    def getdesktopnames(self):
        return self.ewmh.desktopnames

    def getwindowlist(self, stacking=True):
        return self.ewmh.clientliststacking if stacking else self.ewmh.clientlist

    def _getwindow(self, window=None, index=None, stacking=True):
        """ Return window selected by window (id) or index. The index
        is then either based on stacking or creation order depending
        on whether stacking is True. """
        if index is not None:
            win = self.getwindowlist(stacking)[index]
        elif window is not None:
            win = self.root.children[window]
            assert win.window == window
        else:
            # internal error!
            win = None
        return win

class ClientInitMixin:
    """ Common client init. """

    def __init__(self, displayname=None):
        self.display = display.Display(displayname)
        log.debug('%s: connect display=%s', self.__class__.__name__, self.display)
        self.root = window.RootWindow(self.display, self.display.defaultrootwindow)
        self.ewmh = ewmh.EwmhClient(self.display, self.root)
        self.command = command.FootCommandClient(self.display, self.root)
