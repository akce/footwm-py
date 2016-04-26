"""
Minimal Xlib ctypes interface.

Copyright (c) 2016 Akce
"""

import ctypes
import ctypes.util

class EnumMixin(object):

    def _label(self):
        for x in dir(self):
            if getattr(self, x) == self.value:
                return x

    def __str__(self):
        return "{}({}:{})".format(self.__class__.__name__, self._label(), self.value)

xlib = ctypes.CDLL(ctypes.util.find_library('X11'))

# Xlib client side internally uses unsigned long, before converting to correct
# size over the wire. Shouldn't really matter here as ctypes really only uses
# c_int anyway.
Atom = ctypes.c_ulong
XID = ctypes.c_ulong
Window = XID
Time = ctypes.c_ulong

# Xlib Bool predates C99 _Bool, but should come out to the same thing.
Bool = ctypes.c_bool

## Opaque pointer types.
class Display(ctypes.Structure):
    pass
display_p = ctypes.POINTER(Display)
class Screen(ctypes.Structure):
    pass
screen_p = ctypes.POINTER(Screen)

# Error Codes from X.h
class Error(ctypes.c_int, EnumMixin):
    Success              = 0
    BadRequest           = 1    # bad request code
    BadValue             = 2    # int parameter out of range
    BadWindow            = 3    # parameter not a Window
    BadPixmap            = 4    # parameter not a Pixmap
    BadAtom              = 5    # parameter not an Atom
    BadCursor            = 6    # parameter not a Cursor
    BadFont              = 7    # parameter not a Font
    BadMatch             = 8    # parameter mismatch
    BadDrawable          = 9    # parameter not a Pixmap or Window
    BadAccess            =10    # depending on context:
                                # key/button already grabbed
                                # - attempt to free an illegal
                                #   cmap entry
                                # - attempt to store into a read-only
                                #   color map entry.
                                # - attempt to modify the access control
                                #   list from other than the local host.
    BadAlloc             =11    # insufficient resources
    BadColor             =12    # no such colormap
    BadGC                =13    # parameter not a GC
    BadIDChoice          =14    # choice not in range or already used
    BadName              =15    # font or color name doesn't exist
    BadLength            =16    # Request length incorrect
    BadImplementation    =17    # server is defective
    FirstExtensionError  =128
    LastExtensionError   =255

class XErrorEvent(ctypes.Structure):
    _fields_ = [
            ('type', ctypes.c_int),
            ('display', display_p),
            ('resourceid', XID),
            ('serial', ctypes.c_ulong),
            ('error_code', ctypes.c_ubyte),
            ('request_code', ctypes.c_ubyte),
            ('minor_code', ctypes.c_ubyte),
        ]
xerrorevent_p = ctypes.POINTER(XErrorEvent)

# Display *XOpenDisplay(char *display_name);
xlib.XOpenDisplay.restype = display_p
xlib.XOpenDisplay.argtypes = ctypes.c_char_p,

# int XCloseDisplay(Display *display);
xlib.XCloseDisplay.argtypes = display_p,

# /* WARNING, this type not in Xlib spec */
#typedef int (*XErrorHandler) (Display*, XErrorEvent*);
xerrorhandler_p = ctypes.CFUNCTYPE(ctypes.c_int, display_p, xerrorevent_p)

# XErrorHandler XSetErrorHandler (XErrorHandler);
xlib.XSetErrorHandler.restype = xerrorhandler_p
xlib.XSetErrorHandler.argtypes = xerrorhandler_p,

def XSetErrorHandler(handler):
    # XXX Need to keep a reference to xerrorhandler_p object to stop it being gc'd.
    return xlib.XSetErrorHandler(xerrorhandler_p(handler))

# int XSelectInput(Display *display, Window w, long event_mask);
xlib.XSelectInput.argtypes = display_p, Window, ctypes.c_long

# Atom XInternAtom(Display *display, char *atom_name, Bool only_if_exists);
xlib.XInternAtom.restype = Atom
xlib.XInternAtom.argtypes = display_p, ctypes.c_char_p, Bool

# Status XInternAtoms(Display *display, char **names, int count, Bool only_if_exists, Atom *atoms_return);

# char *XGetAtomName(Display *display, Atom atom);
xlib.XGetAtomName.restype = ctypes.c_char_p
xlib.XGetAtomName.argtypes = display_p, Atom

# Status XGetAtomNames(Display *display, Atom *atoms, int count, char **names_return);

## Most macros also have function versions (thankfully!). See Xlib.h

# int XDefaultScreen(Display*);
xlib.XDefaultScreen.argtypes = display_p,

# Window XRootWindow(Display*, int);
xlib.XRootWindow.restype = Window
xlib.XRootWindow.argtypes = display_p, ctypes.c_int

# Window XDefaultRootWindow(Display*);
xlib.XDefaultRootWindow.restype = Window
xlib.XDefaultRootWindow.argtypes = display_p,

# Window XRootWindowOfScreen(Screen*);
xlib.XRootWindowOfScreen.restype = Window
xlib.XRootWindowOfScreen.argtypes = screen_p,

# int XSync(Display *display, Bool discard);
xlib.XSync.argtypes = display_p, Bool

# int XMapWindow(Display *display, Window w);
xlib.XMapWindow.argtypes = display_p, Window

class XAnyEvent(ctypes.Structure):
    _fields_ = [
            ('type', ctypes.c_int),
            ('serial', ctypes.c_ulong),
            ('send_event', Bool),
            ('display', display_p),
            ('window', Window),
            ]

class XKeyEvent(ctypes.Structure):
    _fields_ = [
            ('type', ctypes.c_int),
            ('serial', ctypes.c_ulong),
            ('send_event', ctypes.c_int),
            ('display', display_p),
            ('window', Window),
            ('root', Window),
            ('subwindow', Window),
            ('time', Time),
            ('x', ctypes.c_int),
            ('y', ctypes.c_int),
            ('x_root', ctypes.c_int),
            ('y_root', ctypes.c_int),
            ('state', ctypes.c_uint),
            ('keycode', ctypes.c_uint),
            ('same_screen', Bool),
            ]

class XMapRequestEvent(ctypes.Structure):
    _fields_ = [
            ('type', ctypes.c_int),
            ('serial', ctypes.c_ulong),
            ('send_event', Bool),
            ('display', display_p),
            ('parent', Window),
            ('window', Window),
            ]

class XEvent(ctypes.Union):
    _fields_ = [
            ('type', ctypes.c_int),
            ('xany', XAnyEvent),
            ('xkey', XKeyEvent),
            ('xmaprequest', XMapRequestEvent),
            ('pad', ctypes.c_long * 24),
            ]

# int XNextEvent(Display *display, XEvent *event_return);
xlib.XNextEvent.argtypes = display_p, ctypes.POINTER(XEvent)

## Event definitions. See X.h
class InputEventMask(EnumMixin):
    NoEvent             = 0
    KeyPress            = 1 << 0
    KeyRelease          = 1 << 1
    ButtonPress         = 1 << 2
    ButtonRelease       = 1 << 3
    EnterWindow         = 1 << 4
    LeaveWindow         = 1 << 5
    PointerMotion       = 1 << 6
    PointerMotionHint   = 1 << 7
    Button1Motion       = 1 << 8
    Button2Motion       = 1 << 9
    Button3Motion       = 1 << 10
    Button4Motion       = 1 << 11
    Button5Motion       = 1 << 12
    ButtonMotion        = 1 << 13
    KeymapState         = 1 << 14
    Exposure            = 1 << 15
    VisibilityChange    = 1 << 16
    StructureNotify     = 1 << 17
    ResizeRedirect      = 1 << 18
    SubstructureNotify  = 1 << 19
    SubstructureRedirect = 1 << 20
    FocusChange         = 1 << 21
    PropertyChange      = 1 << 22
    ColormapChange      = 1 << 23
    OwnerGrabButton     = 1 << 24

class EventName(ctypes.c_int, EnumMixin):
    KeyPress            = 2
    KeyRelease          = 3
    ButtonPress         = 4
    ButtonRelease       = 5
    MotionNotify        = 6
    EnterNotify         = 7
    LeaveNotify         = 8
    FocusIn             = 9
    FocusOut            = 10
    KeymapNotify        = 11
    Expose              = 12
    GraphicsExpose      = 13
    NoExpose            = 14
    VisibilityNotify    = 15
    CreateNotify        = 16
    DestroyNotify       = 17
    UnmapNotify         = 18
    MapNotify           = 19
    MapRequest          = 20
    ReparentNotify      = 21
    ConfigureNotify     = 22
    ConfigureRequest    = 23
    GravityNotify       = 24
    ResizeRequest       = 25
    CirculateNotify     = 26
    CirculateRequest    = 27
    PropertyNotify      = 28
    SelectionClear      = 29
    SelectionRequest    = 30
    SelectionNotify     = 31
    ColormapNotify      = 32
    ClientMessage       = 33
    MappingNotify       = 34
    GenericEvent        = 35
    LASTEvent           = 36
