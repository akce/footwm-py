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

from . import log as logmodule
from . import xlib

log = logmodule.make(name=__name__)

class Base:

    def __init__(self, display, windowid):
        """ Initialise EWMH support. """
        super().__init__(display, windowid)
        ## Initialise EWMH ATOMs.
        self.supported = [
                # Supported EWMH atoms.
                '_NET_ACTIVE_WINDOW',
                '_NET_CLIENT_LIST',
                '_NET_CLIENT_LIST_STACKING',
                '_NET_CLOSE_WINDOW',
                '_NET_DESKTOP_NAMES',
                '_NET_SUPPORTING_WM_CHECK',
                '_NET_WM_FULL_PLACEMENT',
                '_NET_WM_NAME',
                ]
        for s in self.supported:
            self.display.add_atom(s)
        self.display.add_atom('_NET_SUPPORTED')

    @property
    def desktopnames(self):
        """ _NET_DESKTOP_NAMES """
        return self.display.gettextproperty(self, '_NET_DESKTOP_NAMES')

    @desktopnames.setter
    def desktopnames(self, names):
        """ _NET_DESKTOP_NAMES """
        self.display.settextproperty(self, names, '_NET_DESKTOP_NAMES')

class ClientRootMixin(Base):
    """ EWMH root window support for client windows. """

    @property
    def clientlist(self):
        """ _NET_CLIENT_LIST """
        return self._getwindows('_NET_CLIENT_LIST')

    @property
    def clientliststacking(self):
        """ _NET_CLIENT_LIST_STACKING """
        return self._getwindows('_NET_CLIENT_LIST_STACKING')

    def _getwindows(self, propname):
        wids = self.display.getpropertywindowids(self, propname)
        for wid in wids:
            if wid not in self.children:
                self.newchild(wid)
        return [self.children[x] for x in wids]

    @property
    def activewindow(self):
        wid = self.display.getpropertywindowid(self, '_NET_ACTIVE_WINDOW')
        try:
            aw = self.children[wid]
        except IndexError:
            aw = self.newchild(wid)
        return aw

    @activewindow.setter
    def activewindow(self, win):
        self.clientmessage('_NET_ACTIVE_WINDOW', win)

    def clientmessage(self, msg, win):
        """ Send an EWMH client message to the window manager.
        See EWMH: Root Window Properties (and Related Messages). """
        eventmask = xlib.InputEventMask.SubstructureNotify | xlib.InputEventMask.SubstructureRedirect
        ev = xlib.XClientMessageEvent()
        ev.type = xlib.EventName.ClientMessage
        ev.window = win.window
        ev.message_type = self.display.atom[msg]
        ev.send_event = True
        ev.format = 32
        return self.display.sendevent(self, ev, eventtype=eventmask)

class WmRootMixin(Base):
    """ EWMH WindowManager Root window support. """

    def __init__(self, display, windowid):
        super().__init__(display, windowid)
        self._installwmsupport()
        self._initsupportingwmcheck()

    def _installwmsupport(self):
        """ Install atoms required by window managers. """
        ls = len(self.supported)
        csupported = (ctypes.c_ulong * ls)()
        for i, s in enumerate(self.supported):
            csupported[i] = self.display.atom[s]
        # TODO see if I can nicely push the ctypes stuff into display.
        self.display.changeproperty(self, '_NET_SUPPORTED', xlib.XA.ATOM, 32, xlib.PropMode.Replace, ctypes.byref(csupported), ls)

    def _initsupportingwmcheck(self):
        """ _NET_SUPPORTING_WM_CHECK """
        # Create the child window for _NET_SUPPORTING_WM_CHECK.
        self._childwindow = self.display.createsimplewindow(self, 0, 0, 1, 1, 0, 0, 0)
        propname = '_NET_SUPPORTING_WM_CHECK'
        cwin = xlib.Window(self._childwindow)
        # Set window id on root window.
        self.display.changeproperty(self, propname, xlib.XA.WINDOW, 32, xlib.PropMode.Replace, ctypes.byref(cwin), 1)
        # Set window id on child window.
        self.display.changeproperty(self._childwindow, propname, xlib.XA.WINDOW, 32, xlib.PropMode.Replace, ctypes.byref(cwin), 1)
        # Set window manager name on child window.
        bname = bytes('footwm', 'utf8')
        blen = len(bname)
        cwinname = (ctypes.c_byte * blen)()
        for i, b in enumerate(bname):
            cwinname[i] = b
        self.display.changeproperty(self._childwindow, '_NET_WM_NAME', self.display.atom['UTF8_STRING'], 8, xlib.PropMode.Replace, ctypes.byref(cwinname), blen)

    @property
    def activewindow(self):
        return super().activewindow

    @activewindow.setter
    def activewindow(self, window):
        """ _NET_ACTIVE_WINDOW """
        cwin = xlib.Window(window.window)
        self.display.changeproperty(self, '_NET_ACTIVE_WINDOW', xlib.XA.WINDOW, 32, xlib.PropMode.Replace, ctypes.byref(cwin), 1)

    @property
    def clientlist(self):
        """ _NET_CLIENT_LIST """
        return super().clientlist

    @property
    def clientliststacking(self):
        """ _NET_CLIENT_LIST_STACKING """
        return super().clientliststacking

    @clientlist.setter
    def clientlist(self, windows):
        """ _NET_CLIENT_LIST """
        self._setwindows(windows, '_NET_CLIENT_LIST')

    @clientliststacking.setter
    def clientliststacking(self, windows):
        """ _NET_CLIENT_LIST_STACKING """
        self._setwindows(windows, '_NET_CLIENT_LIST_STACKING')

    def _setwindows(self, windows, propname):
        lw = len(windows)
        cwindows = (ctypes.c_ulong * lw)()
        for i, w in enumerate(windows):
            cwindows[i] = w.window
        self.display.changeproperty(self, propname, xlib.XA.WINDOW, 32, xlib.PropMode.Replace, ctypes.byref(cwindows), lw)

    def __del__(self):
        self.display.destroywindow(self._childwindow)
        self._childwindow = None

class WmCommandReader:

    def __init__(self, display, root, desktop):
        self.display = display
        self.root = root
        self.desktop = desktop

    def handle_clientmessage(self, msgid, win):
        if msgid == self.display.atom['_NET_ACTIVE_WINDOW']:
            log.debug('0x%08x: _NET_ACTIVE_WINDOW', win.window)
            self.desktop.raisewindow(win=win)
            # Check if raisewindow worked before redrawing.
            # XXX Not sure if i like this....
            if self.desktop.windowlist[0] == win:
                self.desktop.redraw()
        elif msgid == self.display.atom['_NET_CLOSE_WINDOW']:
            win.delete()
            # Do nothing else. We'll receive DestroyNotify etc if the client window is deleted.

__all__ = ClientRootMixin, WmRootMixin, WmCommandReader
