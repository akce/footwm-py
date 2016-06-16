"""
Window classes for footwm.

Copyright (c) 2016 Jerry Kotland
"""

from . import log as xlog
from . import xlib

log = xlog.make(name=__name__)

class WindowError(Exception):
    pass

class Geometry(object):

    def __init__(self, xwinattr):
        self.x = xwinattr.x
        self.y = xwinattr.y
        self.w = xwinattr.width
        self.h = xwinattr.height

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.w == other.w and self.h == other.h

    def __str__(self):
        return '{}(x={}, y={}, w={}, h={})'.format(self.__class__.__name__, self.x, self.y, self.w, self.h)

class BaseWindow(object):

    def __init__(self, display, window):
        self.display = display
        self.window = window
        self._load_window_attr()
        self.name = self.wm_name

    def manage(self, eventmask):
        # watch, maintain, manage, control etc.
        self.display.selectinput(self, eventmask)

    @property
    def wm_name(self):
        #log.debug('0x%08x: Get WM_NAME name=%s status=%d', self.window, name)
        return self.display.getwmname(self)

    def _load_window_attr(self):
        wa = self.display.getwindowattributes(self)
        if wa:
            if wa.override_redirect:
                # No point doing anything else with override_redirect windows. We don't manage them.
                raise WindowError('Ignore window, override_redirect is True')
            # Extract the parts of XWindowAttributes that we need.
            self.geom = Geometry(wa)
            self.map_state = wa.map_state.value
            log.debug('0x%08x: windowattr=%s', self.window, wa)
        else:
            raise WindowError('XGetWindowAttributes failed')

    def __str__(self):
        args = [
                'id=0x{:08x}'.format(self.window),
                'name="{}"'.format(self.name),
                str(self.geom),
                'mapstate={}'.format(self.map_state),
                ]
        # XXX Should abstract this better...
        try:
            if self.res_name:
                args.append('res_name="{}"'.format(self.res_name))
        except AttributeError:
            pass
        try:
            if self.res_class:
                args.append('res_class="{}"'.format(self.res_class))
        except AttributeError:
            pass
        try:
            protocols = self.wm_protocols
        except AttributeError:
            pass
        else:
            if protocols:
                args.append('wm_protocols={}'.format(str(protocols)))
        try:
            if self.transientfor:
                args.append('transientfor=0x{:08x}'.format(self.transientfor.window))
        except AttributeError:
            pass
        try:
            # RootWindow
            if self.children:
                args.append("children=[{}]".format(' '.join('0x{:08x}'.format(x.window) for x in self.children)))
        except AttributeError:
            pass
        return '{}({})'.format(self.__class__.__name__, ' '.join(args))

class RootWindow(BaseWindow):

    def __init__(self, display, window):
        super().__init__(display, window)
        self._import_children()

    def add_child(self, w):
        window = self._make_window(w)
        if window:
            # Add the window to our known list and start managing.
            self.children.insert(0, window)
        return window

    def _import_children(self):
        self.children = []
        for w in self.display.querytree(self):
            window = self._make_window(w)
            if window:
                # WindowError will handle cases where override_redirect=True & XWindowAttributes fails.
                # We have two extra restrictions when importing windows at program startup.
                # Allow import of windows that have MapState=IsViewable, or WM_STATE exists.
                # This is because X has an extra restriction about windows to manage. ie, X apps can create children of the
                # root window, with their override_redirect=False but never Map them and the window manager then has to ignore them.
                # With these checks we're assuming that IsViewable means the window will want to Map itself or that a prior window
                # manager decided to manage the window and added a WM_STATE attribute so we'll manage it too.
                if window.map_state == xlib.MapState.IsViewable:
                    append = True
                elif window.wm_state is not None:
                    append = True
                else:
                    append = False
                if append:
                    self.children.append(window)

    def _make_window(self, windowid):
        """ Window object factory method.
        Will handle creating Normal, Transient managed windows. """
        transientfor = self.display.gettransientfor(windowid)
        log.debug('0x%08x: transientfor=%s', windowid, transientfor)
        try:
            if transientfor is None:
                # Regular window.
                window = NormalWindow(self.display, windowid)
            else:
                window = TransientWindow(self.display, windowid, self.find_child(transientfor))
        except WindowError as e:
            log.debug('0x%08x: %s', windowid, str(e))
            window = None
        else:
            window.manage(xlib.InputEventMask.StructureNotify)
        return window

    def find_child(self, window):
        """ Find a child window object. """
        for w in self.children:
            if window == w.window:
                break
        else:
            w = None
        return w

    def pick(self, index):
        """ Select the family of windows that belong to the window at the given index. """
        window = self.children[index]
        # family accounts for transients
        # TODO window groups. See ICCCM 4.1.11
        family = window.family
        for w in family:
            self.children.remove(w)
        for w in reversed(family):
            self.children.insert(0, w)
        return family

    def remove_child(self, childwin):
        try:
            self.children.remove(childwin)
        except ValueError:
            log.error('0x%08x: Window.remove_child: childwin not found in children window=%s', self.window, childwin)

class ClientWindow(BaseWindow):

    def __init__(self, display, window):
        super().__init__(display, window)
        self.wantedgeom = self.geom
        wm_state = self.wm_state
        self.res_name, self.res_class = self.wm_class
        # The family of windows for a normal client window is only itself.
        self.family = [self]

    def hide(self):
        self.display.unmapwindow(self.window)

    def show(self):
        self.display.mapwindow(self)

    def focus(self):
        msg = 'WM_TAKE_FOCUS'
        try:
            self.clientmessage(msg)
        except KeyError:
            #log.debug('0x%08x: %s not supported', self.window, msg)
            self.display.setinputfocus(self, xlib.InputFocus.RevertToPointerRoot, xlib.CurrentTime)

    def _sendclientmessage(self, atom, time):
        """ Send a ClientMessage event to window. """
        ev = xlib.XClientMessageEvent()
        ev.type = xlib.EventName.ClientMessage
        ev.window = self.window
        ev.message_type = self.display.atom['WM_PROTOCOLS']
        ev.format = 32
        ev.data.l[0] = atom
        ev.data.l[1] = time
        return self.display.sendevent(self, ev)

    def clientmessage(self, msg, time=xlib.CurrentTime):
        """ Send a ClientMessage event to client.
        Will raise a KeyError if WM_PROTOCOLS does not support the msg type. """
        atom = self.wm_protocols[msg]
        status = self._sendclientmessage(atom, time)
        if status:
            log.debug('0x%08x: %s success', self.window, msg)
        else:
            log.error('0x%08x: %s failed', self.window, msg)

    def delete(self):
        """ Sends the WM_PROTOCOLS - WM_DELETE_WINDOW message. """
        # XXX Should we fallback to a destroy window call if this isn't supported?
        msg = 'WM_DELETE_WINDOW'
        try:
            self.clientmessage(msg)
        except KeyError:
            log.debug('0x%08x: %s not supported', self.window, msg)

    # XXX Currently unused.
    @property
    def unmapped(self):
        return self.map_state == self.map_state.IsUnmapped

    @property
    def wm_class(self):
        """ WM_CLASS is a tuple of resource name & class. See ICCCM 4.1.2.5 """
        return self.display.getclasshint(self)

    @property
    def wm_protocols(self):
        """ Return dict(name -> atom) of ATOMs comprising supported WM_PROTOCOLS for the client window. """
        return self.display.getprotocols(self)

    @property
    def wm_state(self):
        state = self.display.getwmstate(self)
        log.debug('0x%08x: Get WM_STATE state=%s', self.window, state)
        return state

    @wm_state.setter
    def wm_state(self, winstate):
        log.debug('0x%08x: Set WM_STATE state=%s', self.window, xlib.WmStateState(winstate))
        self.display.setwmstate(self, winstate)

    def resize(self, geom):
        # Actual geom will be set in the configure notify handler.
        self.wantedgeom = geom
        if self.wantedgeom != self.geom:
            log.debug('0x%08x: attempt resize %s -> %s', self.window, self.geom, self.wantedgeom)
            self.display.moveresizewindow(self, self.wantedgeom.x, self.wantedgeom.y, self.wantedgeom.w, self.wantedgeom.h)

class NormalWindow(ClientWindow):
    pass

class TransientWindow(ClientWindow):

    def __init__(self, display, window, transientfor):
        super().__init__(display, window)
        self.transientfor = transientfor
        # The family of windows for a transient includes the parent, and potentially, that parents parents etc..
        try:
            self.family = [self] + transientfor.family
        except AttributeError:
            # transientfor may not be a managed window (?!) in which case it will be None and have no .family attribute.
            # Xwindows seems to be a land where anything goes!
            # Set the family like a normal window but we'll still draw like a transient.
            self.family = [self]

    @property
    def wantedgeom(self):
        return self._wantedgeom

    @wantedgeom.setter
    def wantedgeom(self, geom):
        # Ignores width/height changes.
        try:
            self._wantedgeom.x = geom.x
        except AttributeError:
            # If this is the first time we've tried to set, then accept the geometry.
            self._wantedgeom = geom
        else:
            # XXX Maybe we should always put in the middle of geom?
            self._wantedgeom.y = geom.y
