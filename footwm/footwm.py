"""
Main footwm module.

Copyright (c) 2016 Akce
"""

# Python standard modules.
import ctypes   # TODO xlib needs to abstract enough so clients don't need ctypes!
import functools
import logging
import sys

# Local modules.
import footwm.xlib as xlib
from . import display
import footwm.kb as kb
import footwm.log

log = footwm.log.make(handler=logging.FileHandler('debug.log'))
log.addHandler(logging.StreamHandler())

def logkey(keyargs):
    wm, window, keysym, keycode, modifiers = keyargs
    log.debug('0x%08x: logkey keysym=%s keycode=%d modifiers=0x%x', window.window, keysym, keycode, modifiers)

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

def get_transientfor(display, windowid):
    """ Is the window a transient (eg, a modal dialog box for another window?).
    If it is, return that window's xwindow id. """
    # TODO see how multiple windows are done for apps like gimp.
    # TODO maybe WM_HINTS:WindowGroupHint
    tf = xlib.Window()
    tstatus = xlib.xlib.XGetTransientForHint(display.xh, windowid, ctypes.byref(tf))
    if tstatus > 0:
        # window is transient, transientfor will contain the window id of the parent window.
        log.debug('0x%08x: transientfor ret=%s for=%s', windowid, tstatus, tf.value)
        transientfor = tf.value
    else:
        transientfor = None
    return transientfor

class BaseWindow(object):

    def __init__(self, display, window):
        self.display = display
        self.window = window
        self._load_window_attr()
        self.name = self.wm_name

    def manage(self, eventmask):
        # watch, maintain, manage, control etc.
        xlib.xlib.XSelectInput(self.display.xh, self.window, eventmask)

    def _sendevent(self, event, eventtype=xlib.InputEventMask.NoEvent):
        """ Do the fancy ctypes event casting before calling XSendEvent. """
        status = xlib.xlib.XSendEvent(self.display.xh, self.window, False, eventtype, ctypes.cast(ctypes.byref(event), xlib.xevent_p))
        return status != 0

    def _xtext_to_lines(self, xtextprop):
        lines = []
        #enc = 'utf8'
        enc = None
        if xtextprop.encoding == xlib.XA.STRING:
            # ICCCM 2.7.1 - XA_STRING == latin-1 encoding.
            enc = 'latin1'
        else:
            atomname = xlib.xlib.XGetAtomName(self.display.xh, xtextprop.encoding)
            log.error('************ UNSUPPORTED TEXT ENCODING ATOM=%s %s', xtextprop.encoding, atomname)
            xlib.xlib.XFree(atomname)
        if enc:
            nitems = ctypes.c_int()
            list_return = ctypes.POINTER(ctypes.c_char_p)()
            status = xlib.xlib.XTextPropertyToStringList(ctypes.byref(xtextprop), ctypes.byref(list_return), ctypes.byref(nitems))
            if status > 0:
                lines = [str(list_return[i], enc) for i in range(nitems.value)]
                #log.debug('xtext lines %s', lines)
                xlib.xlib.XFreeStringList(list_return)
        return lines

    @property
    def wm_name(self):
        name = None
        xtp = xlib.XTextProperty()
        status = xlib.xlib.XGetWMName(self.display.xh, self.window, ctypes.byref(xtp))
        if status > 0:
            #log.debug('xtp %s', xtp)
            if xtp.nitems > 0:
                try:
                    name = self._xtext_to_lines(xtp)[0]
                except IndexError:
                    pass
                xlib.xlib.XFree(xtp.value)
        log.debug('0x%08x: Get WM_NAME name=%s status=%d', self.window, name, status)
        return name

    def _load_window_attr(self):
        wa = xlib.XWindowAttributes()
        astatus = xlib.xlib.XGetWindowAttributes(self.display.xh, self.window, ctypes.byref(wa))
        if astatus > 0:
            # XGetWindowAttr completed successfully.
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
        for w in self.get_children():
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
        transientfor = get_transientfor(self.display, windowid)
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

    def get_children(self):
        a = ctypes.byref        # a = address shorthand.
        root_return = xlib.Window(0)
        parent_of_root = xlib.Window(0)
        childrenp = xlib.window_p()
        nchildren = ctypes.c_uint(0)
        # XXX assert that root_return == root?
        status = xlib.xlib.XQueryTree(self.display.xh, self.window, a(root_return), a(parent_of_root), a(childrenp), a(nchildren))
        children = [childrenp[i] for i in range(nchildren.value)]
        if nchildren.value > 0:
            xlib.xlib.XFree(childrenp)
        return children

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
        xlib.xlib.XUnmapWindow(self.display.xh, self.window)

    def show(self):
        xlib.xlib.XMapWindow(self.display.xh, self.window)

    def focus(self):
        msg = 'WM_TAKE_FOCUS'
        try:
            self.clientmessage(msg)
        except KeyError:
            #log.debug('0x%08x: %s not supported', self.window, msg)
            xlib.xlib.XSetInputFocus(self.display.xh, self.window, xlib.InputFocus.RevertToPointerRoot, xlib.CurrentTime)

    def _sendclientmessage(self, atom, time):
        """ Send a ClientMessage event to window. """
        ev = xlib.XClientMessageEvent()
        ev.type = xlib.EventName.ClientMessage
        ev.window = self.window
        ev.message_type = self.atoms['WM_PROTOCOLS']
        ev.format = 32
        ev.data.l[0] = atom
        ev.data.l[1] = time
        return self._sendevent(ev)

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
        xch = xlib.XClassHint()
        status = xlib.xlib.XGetClassHint(self.display.xh, self.window, ctypes.byref(xch))
        if status > 0:
            # See xlib.py: XClassHint for why we can't use ctypes.c_char_p here.
            ret = str(ctypes.cast(xch.res_name, ctypes.c_char_p).value, 'utf8'), str(ctypes.cast(xch.res_class, ctypes.c_char_p).value, 'utf8')
            if xch.res_name.contents is not None:
                xlib.xlib.XFree(xch.res_name)
            if xch.res_class.contents is not None:
                xlib.xlib.XFree(xch.res_class)
        else:
            ret = "", ""
        return ret

    @property
    def wm_protocols(self):
        """ Return dict(name -> atom) of ATOMs comprising supported WM_PROTOCOLS for the client window. """
        catoms = xlib.atom_p()
        ncount = ctypes.c_int()
        status = xlib.xlib.XGetWMProtocols(self.display.xh, self.window, ctypes.byref(catoms), ctypes.byref(ncount))
        protocols = {}
        if status != 0:
            aids = [catoms[i] for i in range(ncount.value)]
            xlib.xlib.XFree(catoms)
            atomnames = {v: k for k, v in self.atoms.items()}
            for aid in aids:
                try:
                    aname = atomnames[aid]
                except KeyError:
                    caname = xlib.xlib.XGetAtomName(self.display.xh, aid)
                    aname = str(ctypes.cast(caname, ctypes.c_char_p).value, 'latin1')
                    xlib.xlib.XFree(caname)
                    log.debug('0x%08x: Unsupported WM_PROTOCOL atom %s=%d', self.window, aname, aid)
                protocols[aname] = aid
        return protocols

    @property
    def wm_state(self):
        state = None
        a = ctypes.byref        # a = address shorthand.
        WM_STATE = self.atoms['WM_STATE']
        actual_type_return = xlib.Atom()
        actual_format_return = ctypes.c_int()
        nitems_return = ctypes.c_ulong(0)
        bytes_after_return = ctypes.c_ulong()
        prop_return = xlib.byte_p()
        # sizeof return WmState struct in length of longs, not bytes. See XGetWindowProperty
        long_length = int(ctypes.sizeof(xlib.WmState) / ctypes.sizeof(ctypes.c_long))

        ret = xlib.xlib.XGetWindowProperty(self.display.xh, self.window, WM_STATE, 0, long_length, False, WM_STATE, a(actual_type_return), a(actual_format_return), a(nitems_return), a(bytes_after_return), a(prop_return))
        if ret == 0:
            # Success! We need also check if anything was returned..
            if nitems_return.value > 0:
                # This wm doesn't support window icons, so only return WmState.state.
                sp = ctypes.cast(prop_return, xlib.wmstate_p).contents
                state = sp.state
            xlib.xlib.XFree(prop_return)
        log.debug('0x%08x: Get WM_STATE state=%s', self.window, state)
        return state

    @wm_state.setter
    def wm_state(self, winstate):
        state = xlib.WmState()
        state.state = xlib.WmStateState(winstate)
        log.debug('0x%08x: Set WM_STATE state=%s', self.window, state.state)
        state.icon = 0
        WM_STATE = self.atoms['WM_STATE']
        data_p = ctypes.cast(ctypes.byref(state), xlib.byte_p)
        long_length = int(ctypes.sizeof(state) / ctypes.sizeof(ctypes.c_long))
        # Specify as 32 (longs), that way the Xlib client will handle endian translations.
        xlib.xlib.XChangeProperty(self.display.xh, self.window, WM_STATE, WM_STATE, 32, xlib.PropMode.Replace, data_p, long_length)

    def resize(self, geom):
        # Actual geom will be set in the configure notify handler.
        self.wantedgeom = geom
        if self.wantedgeom != self.geom:
            log.debug('0x%08x: attempt resize %s -> %s', self.window, self.geom, self.wantedgeom)
            xlib.xlib.XMoveResizeWindow(self.display.xh, self.window, self.wantedgeom.x, self.wantedgeom.y, self.wantedgeom.w, self.wantedgeom.h)

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

class Foot(object):

    def __init__(self, displayname=None):
        self._atoms = {}
        self.display = display.Display(displayname)
        log.debug('%s: connect display=%s', self.__class__.__name__, self.display)
        self.keyboard = kb.Keyboard(self.display)
        self.keymap = {
                'F5': functools.partial(self.show, 1),
                'F6': functools.partial(self.show, 2),
                'F7': functools.partial(self.show, 3),
                'F8': functools.partial(self.show, 4),
                'F9': functools.partial(self.delete_window, 0),
                }
        self._init_atoms()
        # TODO: worry about screens, displays, xrandr and xinerama!
        self.root = RootWindow(self.display, self.display.defaultrootwindow)
        log.debug('0x%08x: _load_root %s', self.root.window, self.root)
        eventmask = xlib.InputEventMask.StructureNotify | xlib.InputEventMask.SubstructureRedirect | xlib.InputEventMask.SubstructureNotify
        self.display.install(self.root, eventmask)
        # We are now the window manager - continue install.
        # XXX Should we remove WM_ICON_SIZE from root? In case an old WM installed it. See ICCCM 4.1.9
        def xerrorhandler(display, xerrorevent):
            log.error('X Error: %s', xerrorevent)
            return 0
        self.display.errorhandler = xerrorhandler
        self._make_handlers()
        self.install_keymap()
        self.install_keymap(windows=[self.root])
        self.show()

    def _init_atoms(self):
        def aa(symbol, only_if_exists=False):
            self._atoms[symbol] = xlib.xlib.XInternAtom(self.display.xh, bytes(symbol, 'utf8'), only_if_exists)
        aa('WM_STATE')
        aa('WM_PROTOCOLS')
        aa('WM_DELETE_WINDOW')
        aa('WM_TAKE_FOCUS')
        # FIXME need a better organisation for shared atoms...
        BaseWindow.atoms = self._atoms

    def clear_keymap(self):
        for w in self.root.children:
            xlib.xlib.XUngrabKey(self.display.xh, xlib.AnyKey, xlib.GrabKeyModifierMask.AnyModifier, w)

    def install_keymap(self, windows=None):
        """ Installs the window manager top level keymap to selected windows. Install to all managed windows if windows is None. """
        if windows is None:
            ws = self.root.children
        else:
            ws = windows
        for keysymname in self.keymap:
            # TODO handle locked modifiers scroll-lock, num-lock, caps-lock.
            keycode, modifier = self.keyboard.keycodes[keysymname]
            # XXX Should we install the keymap only when the window is focused?
            for w in ws:
                xlib.xlib.XGrabKey(self.display.xh, keycode, modifier, w.window, True, xlib.GrabMode.Async, xlib.GrabMode.Async)

    def _make_handlers(self):
        self.eventhandlers = {
                xlib.EventName.CreateNotify:        self.handle_createnotify,
                xlib.EventName.ConfigureNotify:     self.handle_configurenotify,
                xlib.EventName.ConfigureRequest:    self.handle_configurerequest,
                xlib.EventName.DestroyNotify:       self.handle_destroynotify,
                xlib.EventName.KeyPress:            self.handle_keypress,
                xlib.EventName.MappingNotify:       self.handle_mappingnotify,
                xlib.EventName.MapNotify:           self.handle_mapnotify,
                xlib.EventName.MapRequest:          self.handle_maprequest,
                xlib.EventName.UnmapNotify:         self.handle_unmapnotify,
                }

    def show(self, index=0, keyargs=None):
        """ Pick a child window to bring to front. Any parents of transient windows will also be shown. """
        try:
            family = self.root.pick(index=index)
        except IndexError:
            log.warning('0x{:08x}: pick index={} out of bounds. children len={}'.format(self.root.window, index, len(self.root.children)))
        else:
            # XXX Only select input on mapped (visible) window(s).
            for window in reversed(family):
                window.resize(self.root.geom)
                window.show()
                log.debug('0x%08x: showing window=%s', window.window, window)
            # Focus the very top window.
            if family:
                window.focus()
            # Hide every window that's not in the family of windows.
            for window in self.root.children:
                if window not in family:
                    log.debug('0x%08x: hiding %s', window.window, window)
                    window.hide()

    def delete_window(self, index, keyargs=None):
        """ Delete a window. """
        try:
            w = self.root.children[index]
        except IndexError:
            pass
        else:
            w.delete()
            # Do nothing else. We'll receive DestroyNotify etc if the client window is deleted.

    def run(self):
        event = xlib.XEvent()
        while True:
            try:
                xlib.xlib.XNextEvent(self.display.xh, ctypes.byref(event))
                e = xlib.EventName(event.type)
                #log.debug('event: %s', e)
                try:
                    handler = self.eventhandlers[e.value]
                except KeyError:
                    log.error('unhandled event %s', xlib.EventName(event.type))
                else:
                    handler(event)
            except Exception as e:
                log.exception(e)

    def noop(self, event):
        log.debug('noop %s', xlib.EventName(event.type))

    def handle_createnotify(self, event):
        # New window has been created.
        e = event.xcreatewindow
        geom = Geometry(e)
        log.debug('0x%08x: CreateNotify parent=0x%08x %s override_redirect=%s', e.window, e.parent, geom, e.override_redirect)

    def handle_configurenotify(self, event):
        # The X server has moved and/or resized window e.window
        e = event.xconfigure
        # Only handle if the notify event not caused by a sub-structure redirect.
        if e.event == e.window:
            geom = Geometry(e)
            log.debug('0x%08x: ConfigureNotify %s', e.window, geom)
            window = self.root.find_child(e.window)
            if window:
                window.geom = geom
                if window.wantedgeom == geom:
                    log.debug('0x%08x: current dimensions are good, no need to request again', e.window)
                else:
                    # Window is not the size we want, make a configure request.
                    wg = window.wantedgeom
                    log.debug('0x%08x: requesting again, wanted %s current %s', e.window, window.wantedgeom, window.geom)
                    xlib.xlib.XMoveResizeWindow(self.display.xh, e.window, wg.x, wg.y, wg.w, wg.h)

    def handle_configurerequest(self, event):
        # Some other client tried to reconfigure e.window
        # NOTE: Allow all configure requests, even if their dimensions are not what we want.
        # Most clients get slow and behave weird if they don't get their way, so we'll honour all
        # requests but we'll request the dimensions we want in the callback configure notify handler.
        e = event.xconfigurerequest
        geom = Geometry(e)
        log.debug('0x%08x: ConfigureRequest parent=0x%08x %s %s', e.window, e.parent, geom, e.value_mask)
        wc = xlib.XWindowChanges()
        changemask = 0
        if e.value_mask.value & e.value_mask.CWX:
            changemask |= e.value_mask.CWX
            wc.x = e.x
        if e.value_mask.value & e.value_mask.CWY:
            changemask |= e.value_mask.CWY
            wc.y = e.y
        if e.value_mask.value & e.value_mask.CWWidth:
            changemask |= e.value_mask.CWWidth
            wc.width = e.width
        if e.value_mask.value & e.value_mask.CWHeight:
            changemask |= e.value_mask.CWHeight
            wc.height = e.height
        # Grant requested geom.
        requestedgeom = Geometry(wc)
        log.debug('0x%08x: requested %s %s', e.window, xlib.ConfigureWindowStructure(changemask), requestedgeom)
        xlib.xlib.XConfigureWindow(self.display.xh, e.window, changemask, ctypes.byref(wc))

    def handle_destroynotify(self, event):
        # Window has been destroyed.
        e = event.xdestroywindow
        # Only handle if the notify event not caused by a sub-structure redirect.
        if e.event == e.window:
            log.debug('0x%08x: DestroyNotify event=0x%08x', e.window, e.event)
            # Remove the destroyed window from window hierarchy.
            # This is also now done in the unmapnotify handler where it checks if the window exists or not.
            # Leaving this code here in case the window is destroyed between the call to unmapnotify and this function.
            w = self.root.find_child(e.window)
            if w is None:
                log.debug('0x%08x: not found in root %s', e.window, self.root)
            else:
                self.root.remove_child(w)
                log.debug('0x%08x: removed from root 0x%08x', w.window, self.root.window)
            self.show()

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
                keyargs = (self, self.root.find_child(e.window), keysym, e.keycode, e.state.value)
                keyfunc(keyargs=keyargs)

    def handle_mappingnotify(self, event):
        """ X server has had a keyboard mapping changed. Update our keyboard layer. """
        self.clear_keymap()
        # Recreate keyboard settings.
        self.keyboard = kb.Keyboard(self.display)
        self.install_keymap()

    def handle_mapnotify(self, event):
        # Server has displayed the window.
        e = event.xmap
        # Only handle if the notify event not caused by a sub-structure redirect.
        if e.event == e.window:
            log.debug('0x%08x: MapNotify event=0x%08x override_redirect=%s', e.window, e.event, e.override_redirect)
            # Add a WM_STATE property to the window. See ICCCM 4.1.3.1
            window = self.root.find_child(e.window)
            if window:
                window.wm_state = xlib.WmStateState.Normal
            else:
                log.error('0x%08x: window not found, cannot set WM_STATE=Normal', e.window)

    def handle_maprequest(self, event):
        # A window has requested that it be shown.
        w = event.xmaprequest.window
        window = self.root.find_child(w)
        log.debug('0x%08x: MapRequest known=%s', w, window is not None)
        if window is None:
            p = event.xmaprequest.parent
            window = self.root.add_child(w)
            if window:
                self.install_keymap(windows=[window])
        if window:
            # Put window to the top of the list.
            self.show(index=self.root.children.index(window))

    def handle_unmapnotify(self, event):
        e = event.xunmap
        if e.send_event:
            # The UnmapNotify is because client called something like XWithdrawWindow or XIconifyWindow.
            # Unmap the window, but remove when the xserver sends another UnmapNotify message with send_event=False.
            log.debug('0x%08x: Client requests unmap.. calling XUnmapWindow', e.window)
            xlib.xlib.XUnmapWindow(self.display.xh, e.window)
        else:
            # Only handle if the notify event not caused by a sub-structure redirect. See man XUnmapEvent
            if e.event == e.window:
                # X has unmapped the window, we can now put it in the withdrawn state.
                window = self.root.find_child(e.window)
                if window:
                    # Check that the window still exists!
                    # We have to do this check or else writing to a destroyed window will cause our event loop to halt.
                    # XXX Should we XGrabServer here?
                    wids = self.root.get_children()
                    if window.window in wids:
                        # Mark window Withdrawn. See ICCCM 4.1.3.1
                        window.wm_state = xlib.WmStateState.Withdrawn
                    else:
                        self.root.remove_child(window)
                    log.debug('0x%08x: Unmap successful %s', e.window, window)
                    # Since the window has been unmapped(hidden) show the next window in the list.
                self.show()

    def __del__(self):
        xlib.xlib.XCloseDisplay(self.display.xh)
        self.display = None

def main():
    try:
        foot = Foot()
    except Exception as e:
        log.exception(e)
    foot.run()
