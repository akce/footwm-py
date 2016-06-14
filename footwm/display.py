"""
Display module for footwm.

Display abstracts away most of the direct access to the xlib library.

Copyright (c) 2016 Akce
"""
import ctypes

from . import keydefs
from . import xlib

# addr = address-of, this is a handy shortcut for using ctypes.
addr = ctypes.byref

class DisplayError(Exception):
    """ Error connecting to or managing the display. """
    pass

class Array:
    """ Abstract away x, y access to a linear list. """

    def __init__(self, lst, xwidth):
        self.lst = lst
        self.xwidth = xwidth

    def __call__(self, x, y):
        offset = y * self.xwidth + x
        return self.lst[offset]

class KeySym:

    def __init__(self, keysymid):
        self.keysymid = keysymid
        self.name = keydefs.keysymnames.get(self.keysymid, '???')

    def __hash__(self):
        return hash(self.keysymid)

    def __eq__(self, other):
        return self.keysymid == other.keysymid

    def __str__(self):
        return '{}:0x{:x}'.format(self.name, self.keysymid)

    def __repr__(self):
        """ pprint uses repr to print, so make this nice for our text output. """
        return str(self)

class Display:

    def __init__(self, displayname=None):
        self.displayname = displayname
        #self._errorhandler = None
        # xh = X handle.
        self.xh = xlib.xlib.XOpenDisplay(displayname)
        if self.xh is None:
            raise DisplayError('Failed to connect to display {}'.format(displayname))
        self.atom = {}
        self._nextevent = xlib.XEvent()

    def add_atom(self, symbol, only_if_exists=False):
        self.atom[symbol] = xlib.xlib.XInternAtom(self.xh, bytes(symbol, 'utf8'), only_if_exists)

    def configurewindow(self, window, changemask, windowchanges):
        # XXX Note that window is the number for now.
        xlib.xlib.XConfigureWindow(self.xh, window, changemask, addr(windowchanges))

    @property
    def defaultrootwindow(self):
        return xlib.xlib.XDefaultRootWindow(self.xh)

    @property
    def displaykeycodes(self):
        kmin = ctypes.c_int()
        kmax = ctypes.c_int()
        xlib.xlib.XDisplayKeycodes(self.xh, addr(kmin), addr(kmax))
        return kmin.value, kmax.value

    @property
    def errorhandler(self):
        return self._errorhandler

    @errorhandler.setter
    def errorhandler(self, newhandler):
        # The errorhandler property will store/return the provided newhandler callable.
        self._errorhandler = newhandler
        # Wrap an x error handler func and strip away ctypes specific info before calling.
        def errorfunc(displayp, eventp):
            return newhandler(self, eventp.contents)
        # Need to keep a reference to xerrorhandler_p object to stop it being gc'd.
        self._errorhandlerp = xlib.xerrorhandler_p(errorfunc)
        xlib.xlib.XSetErrorHandler(self._errorhandlerp)

    def free(self, xobject):
        xlib.xlib.XFree(xobject)

    def getatomname(self, atom, encoding='latin1'):
        caname = xlib.xlib.XGetAtomName(self.xh, atom)
        aname = str(ctypes.cast(caname, ctypes.c_char_p).value, encoding)
        self.free(caname)
        return aname

    def getkeyboardmapping(self, keymin, keycount):
        keysyms_per_keycode = ctypes.c_int()
        kbmapping = xlib.xlib.XGetKeyboardMapping(self.xh, keymin, keycount, ctypes.byref(keysyms_per_keycode))
        #print('keysyms/keycode={}'.format(keysyms_per_keycode.value))
        kbarray = Array(kbmapping, keysyms_per_keycode.value)
        # Convert to non-ctypes.
        # dict(keycode=[KeySym])
        ret = dict([(y + keymin, [KeySym(kbarray(x, y)) for x in range(kbarray.xwidth)]) for y in range(keycount)])
        self.free(kbmapping)
        return ret

    def gettransientfor(self, windowid):
        """ Is the window a transient (eg, a modal dialog box for another window?).
        If it is, return that window's xwindow id. """
        tf = xlib.Window()
        tstatus = xlib.xlib.XGetTransientForHint(self.xh, windowid, addr(tf))
        if tstatus > 0:
            # window is transient, transientfor will contain the window id of the parent window.
            transientfor = tf.value
        else:
            transientfor = None
        return transientfor

    def getclasshint(self, window):
        xch = xlib.XClassHint()
        status = xlib.xlib.XGetClassHint(self.xh, window.window, ctypes.byref(xch))
        if status > 0:
            # See xlib.py: XClassHint for why we can't use ctypes.c_char_p here.
            ret = str(ctypes.cast(xch.res_name, ctypes.c_char_p).value, 'utf8'), str(ctypes.cast(xch.res_class, ctypes.c_char_p).value, 'utf8')
            if xch.res_name.contents is not None:
                self.free(xch.res_name)
            if xch.res_class.contents is not None:
                self.free(xch.res_class)
        else:
            ret = "", ""
        return ret

    def getprotocols(self, window):
        catoms = xlib.atom_p()
        ncount = ctypes.c_int()
        status = xlib.xlib.XGetWMProtocols(self.xh, window.window, addr(catoms), addr(ncount))
        protocols = {}
        if status != 0:
            aids = [catoms[i] for i in range(ncount.value)]
            self.free(catoms)
            atomnames = {v: k for k, v in self.atom.items()}
            for aid in aids:
                try:
                    aname = atomnames[aid]
                except KeyError:
                    aname = self.getatomname(aid)
                    #log.debug('0x%08x: Unsupported WM_PROTOCOL atom %s=%d', window.window, aname, aid)
                protocols[aname] = aid
        return protocols

    def getwindowattributes(self, window):
        wa = xlib.XWindowAttributes()
        astatus = xlib.xlib.XGetWindowAttributes(self.xh, window.window, ctypes.byref(wa))
        if astatus > 0:
            # XGetWindowAttr completed successfully.
            ret = wa
        else:
            ret = None
        return ret

    def getwmname(self, window):
        name = None
        xtp = xlib.XTextProperty()
        status = xlib.xlib.XGetWMName(self.xh, window.window, addr(xtp))
        if status > 0:
            #log.debug('xtp %s', xtp)
            if xtp.nitems > 0:
                try:
                    name = self.textprop_to_lines(xtp)[0]
                except IndexError:
                    pass
                self.free(xtp.value)
        return name

    def getwmstate(self, window):
        state = None
        WM_STATE = self.atom['WM_STATE']
        actual_type_return = xlib.Atom()
        actual_format_return = ctypes.c_int()
        nitems_return = ctypes.c_ulong(0)
        bytes_after_return = ctypes.c_ulong()
        prop_return = xlib.byte_p()
        # sizeof return WmState struct in length of longs, not bytes. See XGetWindowProperty
        long_length = int(ctypes.sizeof(xlib.WmState) / ctypes.sizeof(ctypes.c_long))

        ret = xlib.xlib.XGetWindowProperty(self.xh, window.window, WM_STATE, 0, long_length, False, WM_STATE, addr(actual_type_return), addr(actual_format_return), addr(nitems_return), addr(bytes_after_return), addr(prop_return))
        if ret == 0:
            # Success! We need also check if anything was returned..
            if nitems_return.value > 0:
                # This wm doesn't support window icons, so only return WmState.state.
                sp = ctypes.cast(prop_return, xlib.wmstate_p).contents
                state = sp.state
            xlib.xlib.XFree(prop_return)
        return state

    @property
    def keymodifiercodes(self):
        xmodmap = xlib.xlib.XGetModifierMapping(self.xh)
        keypermod = xmodmap.contents.max_keypermod
        modnames = [n for n, _ in xlib.KeyModifierMask._bits_]
        #print('xmodmap.max_keypermod={} modnames={}'.format(keypermod, modnames))
        modarray = Array(xmodmap.contents.modifiermap, keypermod)
        ret = dict([(modnames[y], [modarray(x, y) for x in range(keypermod)]) for y in range(len(modnames))])
        self.free(xmodmap)
        return ret

    def grabkey(self, keycode, modifiermask, grabwindow, ownerevents, pointermode, keyboardmode):
        xlib.xlib.XGrabKey(self.xh, keycode, modifiermask, grabwindow.window, ownerevents, pointermode, keyboardmode)

    def install(self, root, eventmask):
        """ Install ourselves as *the* window manager. """
        def installerror(display, xerrorevent):
            # Only one window can watch SubstructureRedirect on the root window so X will set BadAccess if there's another wm running.
            if xerrorevent.error_code == xlib.Error.BadAccess:
                self.installed = False
            # Need to return an int here - it's ignored, but no explicit return will cause an error.
            return 0
        # Assume we're installed, installerror will set to False if the install fails.
        self.installed = True
        self.errorhandler = installerror
        root.manage(eventmask)
        self.sync()
        if not self.installed:
            raise DisplayError('Another WM is running')

    def mapwindow(self, window):
        xlib.xlib.XMapWindow(self.xh, window.window)

    @property
    def nextevent(self):
        xlib.xlib.XNextEvent(self.xh, addr(self._nextevent))
        return self._nextevent

    def querytree(self, window):
        root_return = xlib.Window(0)
        parent_of_root = xlib.Window(0)
        childrenp = xlib.window_p()
        nchildren = ctypes.c_uint(0)
        # XXX assert that root_return == root?
        status = xlib.xlib.XQueryTree(self.xh, window.window, addr(root_return), addr(parent_of_root), addr(childrenp), addr(nchildren))
        children = [childrenp[i] for i in range(nchildren.value)]
        if nchildren.value > 0:
            self.free(childrenp)
        return children

    def selectinput(self, window, eventmask):
        xlib.xlib.XSelectInput(self.xh, window.window, eventmask)

    def sendevent(self, window, event, eventtype=xlib.InputEventMask.NoEvent):
        """ Do the fancy ctypes event casting before calling XSendEvent. """
        status = xlib.xlib.XSendEvent(self.xh, window.window, False, eventtype, ctypes.cast(ctypes.byref(event), xlib.xevent_p))
        return status != 0

    def setinputfocus(self, window, revertto, time):
        xlib.xlib.XSetInputFocus(self.xh, window.window, revertto, time)

    def setwmstate(self, window, winstate):
        state = xlib.WmState()
        state.state = xlib.WmStateState(winstate)
        state.icon = 0
        WM_STATE = self.atom['WM_STATE']
        data_p = ctypes.cast(addr(state), xlib.byte_p)
        long_length = int(ctypes.sizeof(state) / ctypes.sizeof(ctypes.c_long))
        # Specify as 32 (longs), that way the Xlib client will handle endian translations.
        xlib.xlib.XChangeProperty(self.xh, window.window, WM_STATE, WM_STATE, 32, xlib.PropMode.Replace, data_p, long_length)

    def sync(self, discard=False):
        xlib.xlib.XSync(self.xh, discard)

    def textprop_to_lines(self, xtextprop):
        lines = []
        #enc = 'utf8'
        enc = None
        if xtextprop.encoding == xlib.XA.STRING:
            # ICCCM 2.7.1 - XA_STRING == latin-1 encoding.
            enc = 'latin1'
#        else:
#            atomname = self.getatomname(xtextprop.encoding)
#            #log.error('************ UNSUPPORTED TEXT ENCODING ATOM=%s %s', xtextprop.encoding, atomname)
#            self.free(atomname)
        if enc:
            nitems = ctypes.c_int()
            list_return = ctypes.POINTER(ctypes.c_char_p)()
            status = xlib.xlib.XTextPropertyToStringList(addr(xtextprop), addr(list_return), addr(nitems))
            if status > 0:
                lines = [str(list_return[i], enc) for i in range(nitems.value)]
                #log.debug('xtext lines %s', lines)
                xlib.xlib.XFreeStringList(list_return)
        return lines

    def ungrabkey(self, keycode, modifiermask, grabwindow):
        xlib.xlib.XUngrabKey(self.xh, keycode, modifiermask, grabwindow.window)

    def unmapwindow(self, window):
        # XXX window must be an actual windowid for now. There may still be cases where we need to unmap a window with no associated object.
        xlib.xlib.XUnmapWindow(self.xh, window)

    def __del__(self):
        xlib.xlib.XCloseDisplay(self.xh)
        self.xh = None

    def __str__(self):
        return 'Display({})'.format(self.displayname)
