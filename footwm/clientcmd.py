"""
Client window commands.

Copyright (c) 2016 Akce
"""

import types

from . import display
from . import log as logger
from . import window

log = logger.make(name=__name__)

class ClientCommand:
    """ Higher level X client commands. They will interpret things like indexes etc. """
    def __init__(self, root):
        self.root = root

    def activatewindow(self, stacking=True, index=None, window=None):
        """ Send an EWMH _NET_ACTIVE_WINDOW message to the window manager. """
        win = self._getwindow(stacking=stacking, index=index, window=window)
        if win:
            log.debug("0x%08x: activatewindow index=%s win=%s", win.window, index, win)
            self.root.activewindow = win

    def closewindow(self, stacking=True, index=None, window=None):
        """ Send an ICCCM WM_DELETE_WINDOW message to the window. """
        win = self._getwindow(stacking=stacking, index=index, window=window)
        if win:
            log.debug("0x%08x: closewindow index=%s win=%s", win.window, index, win)
            self.root.closewindow(win)

    def adddesktop(self, name, index):
        self.root.adddesktop(name, index)

    def deletedesktop(self, index):
        self.root.deletedesktop(index)

    def renamedesktop(self, index, name):
        self.root.renamedesktop(index, name)

    def selectdesktop(self, index):
        self.root.currentdesktop = index

    def getdesktopnames(self):
        return self.root.desktopnames

    def getwindowlist(self, stacking=True):
        return self.root.clientliststacking if stacking else self.root.clientlist

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

def makedisplayroot(displayname=None):
    displayobj = display.Display(displayname)
    log.debug('Connect name=%s display=%s', displayname, displayobj)
    root = window.ClientRoot(displayobj, displayobj.defaultrootwindow)
    return displayobj, root
