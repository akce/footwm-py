"""
Main footwm module.

Copyright (c) 2016 Akce
"""

# Python standard modules.
import ctypes   # TODO xlib needs to abstract enough so clients don't need ctypes!
import logging
import sys

# Local modules.
import footwm.xlib as xlib
import footwm.log

log = footwm.log.make(handler=logging.FileHandler('debug.log'))
log.addHandler(logging.StreamHandler())

class WindowError(Exception):
    pass

class Geometry(object):

    def __init__(self, xwinattr):
        self.x = xwinattr.x
        self.y = xwinattr.y
        self.w = xwinattr.width
        self.h = xwinattr.height

    def __str__(self):
        return '{}(x={}, y={}, w={}, h={})'.format(self.__class__.__name__, self.x, self.y, self.w, self.h)

def find_visible(rootwin):
    try:
        visible = rootwin.children[0]
    except IndexError:
        visible = rootwin
    return visible

def find_visible_recursive(rootwin):
    """ Find the visible child window. Note that rootwin will be returned if there's no children. """
    # Finds the highest priority leaf window.
    visible = rootwin
    while True:
        try:
            visible = visible.children[0]
        except IndexError:
            # No more children.
            break
    return visible

def find_window(rootwin, win):
    """ Find window object in a window hierarchy. """
    if rootwin.window == win:
        ret = rootwin
    else:
        for child in rootwin.children:
            ret = find_window(child, win)
            if ret is not None:
                break
        else:
            ret = None
    return ret

class Window(object):

    def __init__(self, display, window, parent=None):
        self.display = display
        self.window = window
        self.parent = parent
        self.children = []
        self._load_window_attr()
        self._load_transientfor()
        wm_state = self.wm_state
        self.name = self.wm_name

    def hide(self):
        xlib.xlib.XUnmapWindow(self.display, self.window)

    def manage(self, eventmask):
        # watch, maintain, manage, control etc.
        xlib.xlib.XSelectInput(self.display, self.window, eventmask)

    def resize(self, geom):
        self.geom = geom
        xlib.xlib.XMoveResizeWindow(self.display, self.window, self.geom.x, self.geom.y, self.geom.w, self.geom.h)

    def show(self):
        xlib.xlib.XMapWindow(self.display, self.window)

    def focus(self):
        xlib.xlib.XSetInputFocus(self.display, self.window, xlib.InputFocus.RevertToPointerRoot, xlib.CurrentTime)

    @property
    def unmapped(self):
        return self.map_state == self.map_state.IsUnmapped

    def remove_child(self, childwin):
        try:
            self.children.remove(childwin)
        except ValueError:
            log.error('0x%08x: Window.remove_child: childwin not found in children window=%s', self.window, childwin)

    def _xtext_to_lines(self, xtextprop):
        lines = []
        #enc = 'utf8'
        enc = None
        if xtextprop.encoding == xlib.XA.STRING:
            # ICCCM 2.7.1 - XA_STRING == latin-1 encoding.
            enc = 'latin1'
        else:
            atomname = xlib.xlib.XGetAtomName(self.display, xtextprop.encoding)
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
        status = xlib.xlib.XGetWMName(self.display, self.window, ctypes.byref(xtp))
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

    @property
    def wm_state(self):
        state = None
        a = ctypes.byref        # a = address shorthand.
        WM_STATE = self.atoms[b'WM_STATE']
        actual_type_return = xlib.Atom()
        actual_format_return = ctypes.c_int()
        nitems_return = ctypes.c_ulong(0)
        bytes_after_return = ctypes.c_ulong()
        prop_return = xlib.byte_p()
        # sizeof return WmState struct in length of longs, not bytes. See XGetWindowProperty
        long_length = int(ctypes.sizeof(xlib.WmState) / ctypes.sizeof(ctypes.c_long))

        ret = xlib.xlib.XGetWindowProperty(self.display, self.window, WM_STATE, 0, long_length, False, WM_STATE, a(actual_type_return), a(actual_format_return), a(nitems_return), a(bytes_after_return), a(prop_return))
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
        WM_STATE = self.atoms[b'WM_STATE']
        data_p = ctypes.cast(ctypes.byref(state), xlib.byte_p)
        long_length = int(ctypes.sizeof(state) / ctypes.sizeof(ctypes.c_long))
        # Specify as 32 (longs), that way the Xlib client will handle endian translations.
        xlib.xlib.XChangeProperty(self.display, self.window, WM_STATE, WM_STATE, 32, xlib.PropMode.Replace, data_p, long_length)

    def _load_window_attr(self):
        wa = xlib.XWindowAttributes()
        astatus = xlib.xlib.XGetWindowAttributes(self.display, self.window, ctypes.byref(wa))
        if astatus > 0:
            # XGetWindowAttr completed successfully.
            # Extract the parts of XWindowAttributes that we need.
            self.geom = Geometry(wa)
            self.override_redirect = wa.override_redirect
            self.map_state = wa.map_state
        else:
            log.error('0x%08x: XGetWindowAttributes failed!', self.window)
            raise WindowError()

    def import_children(self, recurse=False):
        root_return = xlib.Window(0)
        parent_of_root = xlib.Window(0)
        childrenp = xlib.window_p()
        nchildren = ctypes.c_uint(0)

        status = xlib.xlib.XQueryTree(self.display, self.window, ctypes.byref(root_return), ctypes.byref(parent_of_root), ctypes.byref(childrenp), ctypes.byref(nchildren))
        # XXX assert that root_return == root?
        for i in range(nchildren.value):
            try:
                window = Window(self.display, childrenp[i], self.window)
            except WindowError:
                pass
            else:
                self.children.append(window)
        if nchildren.value > 0:
            xlib.xlib.XFree(childrenp)
        if recurse:
            for c in self.children:
                c.import_children()

    def _load_transientfor(self):
        # Is the window a transient (eg, a modal dialog box for another window?)
        # TODO see how multiple windows are done for apps like gimp.
        # TODO maybe WM_HINTS:WindowGroupHint
        # XXX Can we have a transient with no parent?
        tf = xlib.Window()
        tstatus = xlib.xlib.XGetTransientForHint(self.display, self.window, ctypes.byref(tf))
        if tstatus > 0:
            # window is transient, transientfor will contain the window id of the parent window.
            log.debug('0x%08x: transientfor ret=%s for=%s', self.window, tstatus, tf.value)
            self.transientfor = tf.value
        else:
            self.transientfor = None

    def __str__(self):
        args = [
                'id=0x{:08x}'.format(self.window),
#                '"name={}"'.format(self.name),
                str(self.geom),
                'mapstate={}'.format(self.map_state),
                'override_redirect={}'.format(self.override_redirect),
                ]
        if self.parent:
            args.append('parent=0x{:08x}'.format(self.parent))
        if self.transientfor:
            args.append('transientfor=0x{:08x}'.format(self.transientfor))
        if self.children:
            args.append("children=[{}]".format(' '.join('0x{:08x}'.format(x.window) for x in self.children)))
        return 'Window({})'.format(' '.join(args))

def xerrorhandler(display_p, event_p):
    event = event_p.contents
    log.error('X Error: %s', event)
    return 0

class Foot(object):

    def __init__(self, displayname=None):
        # The shown window is always at index 0.
        self._atoms = {}
        self.display = xlib.xlib.XOpenDisplay(displayname)
        self._init_atoms()
        log.debug('x connect displayname=%s', displayname) #, self.display.contents)
        self._load_root()
        self._install_wm()
        self._make_handlers()
        self._show()

    def _load_root(self):
        # TODO: worry about screens, displays, xrandr and xinerama!
        self.root = Window(self.display, xlib.xlib.XDefaultRootWindow(self.display))
        self.root.import_children()
        log.debug('0x%08x: _load_root %s', self.root.window, self.root)

    def _init_atoms(self):
        def aa(symbol, only_if_exists=False):
            self._atoms[symbol] = xlib.xlib.XInternAtom(self.display, symbol, only_if_exists)
        aa(b'WM_STATE')
        # FIXME need a better organisation for shared atoms...
        Window.atoms = self._atoms

    def _make_handlers(self):
        self.eventhandlers = {
                xlib.EventName.CreateNotify:        self.handle_createnotify,
                xlib.EventName.ConfigureNotify:     self.handle_configurenotify,
                xlib.EventName.ConfigureRequest:    self.handle_configurerequest,
                xlib.EventName.DestroyNotify:       self.handle_destroynotify,
                xlib.EventName.MapNotify:           self.handle_mapnotify,
                xlib.EventName.MapRequest:          self.handle_maprequest,
                xlib.EventName.UnmapNotify:         self.handle_unmapnotify,
                }

    def _add_window(self, window):
        if window.override_redirect:
            log.debug('0x%08x: _add_window ignoring, override_redirect is True', window.window)
            # XXX Add to a list as well?
        else:
            # Find the parent window object and insert this window into its children list.
            parent = find_window(self.root, window.parent)
            if parent:
                parent.children.insert(0, window)
                # Add the window to our known list and make sure it's withdrawn (not-visible).
                # Once footwm finishes startup, we'll get it to show the highest priority window in the list.
                # All normal windows are kept in the withdrawn state unless they're on the top of the MRU stack.
                window.manage(xlib.InputEventMask.StructureNotify)
#               # XXX is this right? XWindowAttributes are what the client wants or the actual state?
#               if window.unmapped:
#                   # Add a WM_STATE property to the window. See ICCCM 4.1.3.1
#                   window.wm_state = xlib.WmStateState.Withdrawn
#               else:
#                   window.hide()
                log.debug('0x%08x: _add_window added to %s', window.window, parent)
            else:
                log.error('0x%08x: _add_window parent 0x%08x not found, ignoring window', window.window, window.parent)

    def _show(self):
        """ Show the highest priority window. """
        # XXX Only select input on mapped (visible) window(s).
        # TODO assert all windows are withdrawn?
        try:
            window = find_visible(self.root)
        except IndexError:
            # Windows list is empty, nothing to do.
            pass
        else:
            if window:
                log.debug('0x%08x: showing window=%s', window.window, window)
                window.resize(self.root.geom)
                window.show()
                window.focus()
            else:
                log.info('_show: no visible windows')

    def _install_wm(self):
        """ Install foot as *the* window manager. """
        # Assume we can install, wmerrhandler will tell us if we can't be the window manager.
        installed = True
        def wmerrhandler(display_p, event_p):
            nonlocal installed
            # XSelectInput(rootwin) will set BadAccess if there's another wm running.
            if event_p.contents.error_code == xlib.Error.BadAccess:
                installed = False
            # Need to return an int here - it's ignored. No explicit return will cause an error.
            return 0
        olderrorhandler = xlib.XSetErrorHandler(wmerrhandler)
        self.root.manage(xlib.InputEventMask.StructureNotify | xlib.InputEventMask.SubstructureRedirect | xlib.InputEventMask.SubstructureNotify)
        xlib.xlib.XSync(self.display, False)
        if installed:
            # We are now the window manager - continue install.
            # XXX Should we remove WM_ICON_SIZE from root? In case an old WM installed it. See ICCCM 4.1.9
            # Install X error handler.
            xlib.XSetErrorHandler(xerrorhandler)
        else:
            # Exit.
            log.error('Another WM is already running!')
            sys.exit(1)

    def run(self):
        event = xlib.XEvent()
        while True:
            try:
                xlib.xlib.XNextEvent(self.display, ctypes.byref(event))
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
        self._add_window(Window(self.display, e.window, e.parent))
        self._show()

    def handle_configurenotify(self, event):
        # The X server has moved and/or resized window e.window
        e = event.xconfigure
        # Only handle if the notify event not caused by a sub-structure redirect.
        if e.event == e.window:
            geom = Geometry(e)
            log.debug('0x%08x: ConfigureNotify %s', e.window, geom)

    def handle_configurerequest(self, event):
        # Some other client tried to reconfigure e.window
        e = event.xconfigurerequest
        geom = Geometry(e)
        log.debug('0x%08x: ConfigureRequest parent=0x%08x %s %s', e.window, e.parent, geom, e.value_mask)
        # TODO allow configurerequest for transients, ignore for normal windows?
        # XXX Check if e.window is current window?
        # FIXME allow all configure requests for now.
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
        log.debug('0x%08x: granted %s %s', e.window, xlib.ConfigureWindowStructure(changemask), Geometry(wc))
        xlib.xlib.XConfigureWindow(self.display, e.window, changemask, ctypes.byref(wc))
        xlib.xlib.XSync(self.display, False)

    def handle_destroynotify(self, event):
        # Window has been destroyed.
        e = event.xdestroywindow
        # Only handle if the notify event not caused by a sub-structure redirect.
        if e.event == e.window:
            log.debug('0x%08x: DestroyNotify event=0x%08x', e.window, e.event)
            # Remove window from window hierarchy.
            w = find_window(self.root, e.window)
            if w is None:
                log.error('0x%08x: not found in root %s', e.window, self.root)
            else:
                p = find_window(self.root, w.parent)
                if p is None:
                    log.error('0x%08x: parent 0x%08x not found', e.window, w.parent)
                else:
                    p.remove_child(w)
                    log.debug('0x%08x: removed from %s', w.window, p)

    def handle_mapnotify(self, event):
        # Server has displayed the window.
        e = event.xmap
        # Only handle if the notify event not caused by a sub-structure redirect.
        if e.event == e.window:
            log.debug('0x%08x: MapNotify event=0x%08x override_redirect=%s', e.window, e.event, e.override_redirect)
            window = find_window(self.root, e.window)
            if window:
                window.wm_state = xlib.WmStateState.Normal
            else:
                log.error('0x%08x: window not found, cannot set WM_STATE=Normal', e.window)

    def handle_maprequest(self, event):
        # A window has requested that it be shown.
        w = event.xmaprequest.window
        window = find_window(self.root, w)
        log.debug('0x%08x: MapRequest known=%s', w, window is not None)
        # Display if window is top of the display list.
        if window is find_visible(self.root):
            log.debug('0x%08x: window is top of the list, displaying', w)
            xlib.xlib.XMapWindow(self.display, w)
        else:
            # Reject map request since the window is not to be displayed.
            log.debug('0x%08x: window is not top of the list, not displaying', w)

    def handle_unmapnotify(self, event):
        e = event.xunmap
        if e.send_event:
            # The UnmapNotify is because client called something like XWithdrawWindow or XIconifyWindow.
            # Unmap the window, but remove when the xserver sends another UnmapNotify message with send_event=False.
            log.debug('0x%08x: Client requests unmap.. calling XUnmapWindow', e.window)
            xlib.xlib.XUnmapWindow(self.display, e.window)
        else:
            # Only handle if the notify event not caused by a sub-structure redirect. See man XUnmapEvent
            if e.event == e.window:
                # X has unmapped the window, we can now put it in the withdrawn state.
                window = find_window(self.root, e.window)
                if window:
                    log.debug('0x%08x: Unmap successful', e.window)
                    # FIXME this causes the segfault on wm shutdown!
                    window.wm_state = xlib.WmStateState.Withdrawn
                # TODO now draw next priority window?

    def __del__(self):
        xlib.xlib.XCloseDisplay(self.display)
        self.display = None

def main():
    try:
        foot = Foot()
    except Exception as e:
        log.exception(e)
    foot.run()
