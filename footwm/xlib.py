"""
Minimal Xlib ctypes interface.

Copyright (c) 2016 Akce
"""

import ctypes
import ctypes.util

# Resource constants X.h
PointerRoot = 1
CurrentTime = 0

class EnumMixin(object):

    def _label(self):
        for x in dir(self):
            if getattr(self, x) == self.value:
                return x

    def __str__(self):
        return "{}({}:{})".format(self.__class__.__name__, self._label(), self.value)

def BitmapMetaMaker(ct):
    """ BitmapMeta class maker.

    BitmapMeta classes augment ctypes number classes with knowledge of bits and
    an improved string representation.

    To use, define available bits in the _bits_ list. Note, we're not using the
    same _fields_ attribute that ctypes uses to avoid a potential clash in case
    ctypes number classes ever decide to use. _bits_ also makes more sense than
    _fields_ for a bitmap.

    Typical use is something like:

        >>> class XBitmap(ctypes.c_long, metaclass=BitmapMetaMaker(ctypes.c_long)):
        >>>     _bits_ = [ ('name1', (1 << 0)), ('name2', (1 << 1)), ]
        >>> b = XBitmap(XBitmap.name1 | XBitmap.name2)
        >>> str(b)
        XBitmap(name1:0x01|name2:0x02)

    We can't define a simple metaclass because all the ctypes classes I've used
    define their own metaclass so we need to mix theirs and this one.
    """
    class BitmapMeta(type(ct)):
        def __init__(cls, name, bases, dct):
            super().__init__(name, bases, dct)
            # Add a class attribute for every _bits_ entry.
            for label, bit in cls._bits_:
                setattr(cls, label, bit)

            def __str__(self):
                return '{}({})'.format(self.__class__.__name__, '|'.join(['{}:0x{:02x}'.format(label, i) for label, i in self._bits_ if self.value & i]))
            setattr(cls, '__str__', __str__)
    return BitmapMeta

xlib = ctypes.CDLL(ctypes.util.find_library('X11'))

# Xlib client side internally uses unsigned long, before converting to correct
# size over the wire. Shouldn't really matter here as ctypes really only uses
# c_int anyway.
Atom = ctypes.c_ulong
XID = ctypes.c_ulong
Colormap = XID
Window = XID
Time = ctypes.c_ulong
Status = ctypes.c_int

atom_p = ctypes.POINTER(Atom)
window_p = ctypes.POINTER(Window)

# Xlib Bool predates C99 _Bool, but should come out to the same thing.
Bool = ctypes.c_bool

byte_p = ctypes.POINTER(ctypes.c_ubyte)
long_p = ctypes.POINTER(ctypes.c_long)
ulong_p = ctypes.POINTER(ctypes.c_ulong)
int_p = ctypes.POINTER(ctypes.c_int)
char_p = ctypes.POINTER(ctypes.c_char)

## Opaque pointer types.
class Display(ctypes.Structure):
    pass
display_p = ctypes.POINTER(Display)
class Screen(ctypes.Structure):
    pass
screen_p = ctypes.POINTER(Screen)
class Visual(ctypes.Structure):
    pass
visual_p = ctypes.POINTER(Visual)

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

    def __str__(self):
        # Convert error_code byte to Error int.
        err = Error(self.error_code)
        return '{}(type={}, resource=0x{:08x} serial={} error={} request={} minor={})'.format(self.__class__.__name__, self.type, self.resourceid, self.serial, err, self.request_code, self.minor_code)

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

# int XMapWindow(Display *display, Window w);
xlib.XUnmapWindow.argtypes = display_p, Window

# Status XQueryTree(Display *display, Window w, Window *root_return, Window *parent_return, Window **children_return, unsigned int *nchildren_return);
xlib.XQueryTree.restype = Status
xlib.XQueryTree.argtypes = display_p, Window, window_p, window_p, ctypes.POINTER(window_p), ctypes.POINTER(ctypes.c_uint)

# Status XGetTransientForHint(Display *display, Window w, Window *prop_window_return);
xlib.XGetTransientForHint.restype = Status
xlib.XGetTransientForHint.argtypes = display_p, Window, window_p

# Window XCreateSimpleWindow(Display *display, Window parent, int x, int y, unsigned int width, unsigned int height, unsigned int border_width, unsigned long border, unsigned long background);
xlib.XCreateSimpleWindow.restype = Window
xlib.XCreateSimpleWindow.argtypes = display_p, Window, ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_ulong, ctypes.c_ulong

# int XDestroyWindow(Display *display, Window w);
xlib.XDestroyWindow.argtypes = display_p, Window

# int XFree(void *data);
xlib.XFree.argtypes = ctypes.c_void_p,

class XAnyEvent(ctypes.Structure):
    _fields_ = [
            ('type', ctypes.c_int),
            ('serial', ctypes.c_ulong),
            ('send_event', Bool),
            ('display', display_p),
            ('window', Window),
            ]

class XClientMessageEvent(ctypes.Structure):
    class _Data(ctypes.Union):
        _fields_ = [
                ('b', ctypes.c_char * 20),
                ('s', ctypes.c_short * 10),
                ('l', ctypes.c_long * 5),
                ]
    _fields_ = [
            ('type', ctypes.c_int),
            ('serial', ctypes.c_ulong),
            ('send_event', Bool),
            ('display', display_p),
            ('window', Window),
            ('message_type', Atom),
            ('format', ctypes.c_int),
            ('data', _Data),
            ]

class StackingMethod(ctypes.c_int, EnumMixin):
    Above =     0
    Below =     1
    TopIf =     2
    BottomIf =  3
    Opposite =  4

class KeyModifierMask(ctypes.c_uint, metaclass=BitmapMetaMaker(ctypes.c_uint)):
    _bits_ = [
            ('Shift',   (1<<0)),
            ('Lock',    (1<<1)),
            ('Control', (1<<2)),
            ('Mod1',    (1<<3)),
            ('Mod2',    (1<<4)),
            ('Mod3',    (1<<5)),
            ('Mod4',    (1<<6)),
            ('Mod5',    (1<<7)),
            ]

class GrabKeyModifierMask(ctypes.c_uint, metaclass=BitmapMetaMaker(ctypes.c_uint)):
    _bits_ = KeyModifierMask._bits_ + [('AnyModifier', (1<<15))]

class ConfigureWindowStructure(ctypes.c_ulong, metaclass=BitmapMetaMaker(ctypes.c_ulong)):
    _bits_ = [
        ('CWX',             (1<<0)),
        ('CWY',             (1<<1)),
        ('CWWidth',         (1<<2)),
        ('CWHeight',        (1<<3)),
        ('CWBorderWidth',   (1<<4)),
        ('CWSibling',       (1<<5)),
        ('CWStackMode',     (1<<6)),
        ]

class XCreateWindowEvent(ctypes.Structure):
    _fields_ = [
            ('type', ctypes.c_int),
            ('serial', ctypes.c_ulong),
            ('send_event', Bool),
            ('display', display_p),
            ('parent', Window),
            ('window', Window),
            ('x', ctypes.c_int),
            ('y', ctypes.c_int),
            ('width', ctypes.c_int),
            ('height', ctypes.c_int),
            ('border_width', ctypes.c_int),
            ('override_redirect', Bool),
            ]

class XConfigureEvent(ctypes.Structure):
    _fields_ = [
            ('type', ctypes.c_int),
            ('serial', ctypes.c_ulong),
            ('send_event', Bool),
            ('display', display_p),
            ('event', Window),
            ('window', Window),
            ('x', ctypes.c_int),
            ('y', ctypes.c_int),
            ('width', ctypes.c_int),
            ('height', ctypes.c_int),
            ('border_width', ctypes.c_int),
            ('above', Window),
            ('override_redirect', Bool),
            ]

class XConfigureRequestEvent(ctypes.Structure):
    _fields_ = [
            ('type', ctypes.c_int),
            ('serial', ctypes.c_ulong),
            ('send_event', Bool),
            ('display', display_p),
            ('parent', Window),
            ('window', Window),
            ('x', ctypes.c_int),
            ('y', ctypes.c_int),
            ('width', ctypes.c_int),
            ('height', ctypes.c_int),
            ('border_width', ctypes.c_int),
            ('above', Window),
            ('detail', StackingMethod),
            ('value_mask', ConfigureWindowStructure),
            ]

class XDestroyWindowEvent(ctypes.Structure):
    _fields_ = [
            ('type', ctypes.c_int),
            ('serial', ctypes.c_ulong),
            ('send_event', Bool),
            ('display', display_p),
            ('event', Window),
            ('window', Window),
            ]

class FocusMode(ctypes.c_int, EnumMixin):
    NotifyNormal        = 0
    NotifyGrab          = 1
    NotifyUngrab        = 2
    NotifyWhileGrabbed  = 3

class FocusDetail(ctypes.c_int, EnumMixin):
    NotifyAncestor          = 0
    NotifyVirtual           = 1
    NotifyInferior          = 2
    NotifyNonlinear         = 3
    NotifyNonlinearVirtual  = 4
    NotifyPointer           = 5
    NotifyPointerRoot       = 6
    NotifyDetailNone        = 7

class XFocusChangeEvent(ctypes.Structure):
    _fields_ = [
            ('type', ctypes.c_int),
            ('serial', ctypes.c_ulong),
            ('send_event', Bool),
            ('display', display_p),
            ('window', Window),
            ('mode', FocusMode),
            ('detail', FocusDetail),
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
            ('state', KeyModifierMask),
            ('keycode', ctypes.c_uint),
            ('same_screen', Bool),
            ]

class XMapEvent(ctypes.Structure):
    _fields_ = [
            ('type', ctypes.c_int),
            ('serial', ctypes.c_ulong),
            ('send_event', Bool),
            ('display', display_p),
            ('event', Window),
            ('window', Window),
            ('override_redirect', Bool),
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

class XUnmapEvent(ctypes.Structure):
    _fields_ = [
            ('type', ctypes.c_int),
            ('serial', ctypes.c_ulong),
            ('send_event', Bool),
            ('display', display_p),
            ('event', Window),
            ('window', Window),
            ('from_configure', Bool),
            ]

class XEvent(ctypes.Union):
    _fields_ = [
            ('type', ctypes.c_int),
            ('xany', XAnyEvent),
            ('xclient', XClientMessageEvent),
            ('xcreatewindow', XCreateWindowEvent),
            ('xconfigure', XConfigureEvent),
            ('xconfigurerequest', XConfigureRequestEvent),
            ('xdestroywindow', XDestroyWindowEvent),
            ('xfocus', XFocusChangeEvent),
            ('xkey', XKeyEvent),
            ('xmap', XMapEvent),
            ('xmaprequest', XMapRequestEvent),
            ('xunmap', XUnmapEvent),
            ('pad', ctypes.c_long * 24),
            ]

xevent_p = ctypes.POINTER(XEvent)

# int XNextEvent(Display *display, XEvent *event_return);
xlib.XNextEvent.argtypes = display_p, xevent_p

## Event definitions. See X.h
class InputEventMask(ctypes.c_long, metaclass=BitmapMetaMaker(ctypes.c_long)):
    _bits_ = [
            ('NoEvent',             (0)),
            ('KeyPress',            (1 << 0)),
            ('KeyRelease',          (1 << 1)),
            ('ButtonPress',         (1 << 2)),
            ('ButtonRelease',       (1 << 3)),
            ('EnterWindow',         (1 << 4)),
            ('LeaveWindow',         (1 << 5)),
            ('PointerMotion',       (1 << 6)),
            ('PointerMotionHint',   (1 << 7)),
            ('Button1Motion',       (1 << 8)),
            ('Button2Motion',       (1 << 9)),
            ('Button3Motion',       (1 << 10)),
            ('Button4Motion',       (1 << 11)),
            ('Button5Motion',       (1 << 12)),
            ('ButtonMotion',        (1 << 13)),
            ('KeymapState',         (1 << 14)),
            ('Exposure',            (1 << 15)),
            ('VisibilityChange',    (1 << 16)),
            ('StructureNotify',     (1 << 17)),
            ('ResizeRedirect',      (1 << 18)),
            ('SubstructureNotify',  (1 << 19)),
            ('SubstructureRedirect',(1 << 20)),
            ('FocusChange',         (1 << 21)),
            ('PropertyChange',      (1 << 22)),
            ('ColormapChange',      (1 << 23)),
            ('OwnerGrabButton',     (1 << 24)),
            ]

# int XMaskEvent(Display *display, long event_mask, XEvent *event_return);
xlib.XMaskEvent.argtypes = display_p, InputEventMask, xevent_p

# Status XSendEvent(Display *display, Window w, Bool propagate, long event_mask, XEvent *event_send);
xlib.XSendEvent.restype = Status
xlib.XSendEvent.argtypes = display_p, Window, Bool, InputEventMask, xevent_p

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

# Only define current ICCCM values. See Xutil.h
class MapState(ctypes.c_int, EnumMixin):
    IsUnmapped      = 0
    IsUnviewable    = 1
    IsViewable      = 2

class WindowClass(ctypes.c_int, EnumMixin):
    CopyFromParent  = 0
    InputOutput     = 1
    InputOnly       = 2

class BitGravity(ctypes.c_int, EnumMixin):
    Forget          = 0
    NorthWest       = 1
    North           = 2
    NorthEast       = 3
    West            = 4
    Center          = 5
    East            = 6
    SouthWest       = 7
    South           = 8
    SouthEast       = 9
    Static          = 10

# WindowGravity == BitGravity ~= s/Forget/Unmap/
class WindowGravity(ctypes.c_int, EnumMixin):
    Unmap           = 0
    NorthWest       = 1
    North           = 2
    NorthEast       = 3
    West            = 4
    Center          = 5
    East            = 6
    SouthWest       = 7
    South           = 8
    SouthEast       = 9
    Static          = 10

class XWindowAttributes(ctypes.Structure):
    _fields_ = [
            ('x', ctypes.c_int),
            ('y', ctypes.c_int),
            ('width', ctypes.c_int),
            ('height', ctypes.c_int),
            ('border_width', ctypes.c_int),
            ('depth', ctypes.c_int),
            ('visual', visual_p),
            ('root', Window),
            ('cls', WindowClass),
            ('bit_gravity', BitGravity),
            ('win_gravity', WindowGravity),
            ('backing_store', ctypes.c_int),
            ('backing_planes', ctypes.c_ulong),
            ('backing_pixel', ctypes.c_ulong),
            ('save_under', Bool),
            ('colormap', Colormap),
            ('map_installed', Bool),
            ('map_state', MapState),
            ('all_event_masks', InputEventMask),
            ('your_event_mask', InputEventMask),
            ('do_not_propagate_mask', InputEventMask),
            ('override_redirect', Bool),
            ('screen', screen_p),
            ]

    def __str__(self):
        # TODO for now only show non-footwm.Geometry info.
        return 'borderw={} depth={} root=0x{:08x} class={} bitgravity={} wingravity={} map_state={}'.format(self.border_width, self.depth, self.root, self.cls, self.bit_gravity, self.win_gravity, self.map_state)

# XChangeProperty modes. See X.h
class PropMode(ctypes.c_int, EnumMixin):
    Replace         = 0
    Prepend         = 1
    Append          = 2

# WM_STATE window state. See Xutil.h & ICCCM 4.1.3.1
class WmStateState(ctypes.c_int, EnumMixin):
    Withdrawn   = 0
    Normal      = 1
    Iconic      = 3

class WmState(ctypes.Structure):
    _fields_ = [
            ('state', WmStateState),
            ('icon', Window),
            ]
    def __str__(self):
        return "{}({} icon={})".format(self.__class__.__name__, str(self.state), self.icon)

wmstate_p = ctypes.POINTER(WmState)

# Status XGetWindowAttributes(Display *display, Window w, XWindowAttributes *window_attributes_return);
xlib.XGetWindowAttributes.restype = Status
xlib.XGetWindowAttributes.argtypes = display_p, Window, ctypes.POINTER(XWindowAttributes)

# int XChangeProperty(Display *display, Window w, Atom property, Atom type, int format, int mode, unsigned char *data, int nelements);
xlib.XChangeProperty.argtypes = display_p, Window, Atom, Atom, ctypes.c_int, PropMode, byte_p, ctypes.c_int

# int XGetWindowProperty(Display *display, Window w, Atom property, long long_offset, long long_length, Bool delete, Atom req_type, Atom
#              *actual_type_return, int *actual_format_return, unsigned long *nitems_return, unsigned long *bytes_after_return, unsigned char
#              **prop_return);
xlib.XGetWindowProperty.argtypes = display_p, Window, Atom, ctypes.c_long, ctypes.c_long, Bool, Atom, atom_p, int_p, ulong_p, ulong_p, ctypes.POINTER(byte_p)

class XClassHint(ctypes.Structure):
    _fields_ = [
            # NOTE: do *not* use c_char_p here. ctypes will automatically convert them to python str and discard the c-pointers. We have to retain
            # the pointers in order to free them via xlib.XFree. Clients will need to cast these to c_char_p before creating the str.
            ('res_name', char_p),
            ('res_class', char_p),
            ]

# Status XGetClassHint(Display *display, Window w, XClassHint *class_hints_return);
xlib.XGetClassHint.restype = Status
xlib.XGetClassHint.argtypes = display_p, Window, ctypes.POINTER(XClassHint)

# char *XGetAtomName(Display *display, Atom atom);
xlib.XGetAtomName.restype = char_p
xlib.XGetAtomName.argtypes = display_p, Atom

# Status XGetWMProtocols(Display *display, Window w, Atom **protocols_return, int *count_return);
xlib.XGetWMProtocols.restype = Status
xlib.XGetWMProtocols.argtypes = display_p, Window, ctypes.POINTER(atom_p), int_p,

class XWindowChanges(ctypes.Structure):
    _fields_ = [
            ('x', ctypes.c_int),
            ('y', ctypes.c_int),
            ('width', ctypes.c_int),
            ('height', ctypes.c_int),
            ('border_width', ctypes.c_int),
            ('sibling', Window),
            ('stack_mode', StackingMethod),
            ]
xwindowchanges_p = ctypes.POINTER(XWindowChanges)

# int XConfigureWindow(Display *display, Window w, unsigned value_mask, XWindowChanges *changes);
xlib.XConfigureWindow.argtypes = display_p, Window, ConfigureWindowStructure, xwindowchanges_p

# int XMoveResizeWindow(Display *display, Window w, int x, int y, unsigned width, unsigned height);
xlib.XMoveResizeWindow.argtypes = display_p, Window, ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint

# X protocol atoms, see Xatom.h
class XA(ctypes.c_ulong, EnumMixin):
    ATOM        = 4
    STRING      = 31
    WINDOW      = 33

# Xutil.h
class XICCEncodingStyle(ctypes.c_ulong, EnumMixin):
    String         = 0
    CompoundText   = 1
    Text           = 2
    StdICCText     = 3
    UTF8String     = 4

class XTextProperty(ctypes.Structure):
    _fields_ = [
            ('value', byte_p),
            ('encoding', Atom),
            ('format', ctypes.c_int),
            ('nitems', ctypes.c_ulong),
            ]
    def __str__(self):
        return '{}(value={}, encoding={}, format={}, nitems={})'.format(self.__class__.__name__, self.value, self.encoding, self.format, self.nitems)

xtextproperty_p = ctypes.POINTER(XTextProperty)

# Status XGetWMName(Display *display, Window w, XTextProperty *text_prop_return);
xlib.XGetWMName.restype = Status
xlib.XGetWMName.argtypes = display_p, Window, xtextproperty_p

# void XFreeStringList(char **list);
xlib.XFreeStringList.restype = None
xlib.XFreeStringList.argtypes = ctypes.POINTER(ctypes.c_char_p),

# Status XTextPropertyToStringList(XTextProperty *text_prop, char ***list_return, int *count_return);
xlib.XTextPropertyToStringList.restype = Status
xlib.XTextPropertyToStringList.argtypes = xtextproperty_p, ctypes.POINTER(ctypes.POINTER(ctypes.c_char_p)), int_p

class InputFocus(ctypes.c_int, EnumMixin):
    RevertToNone        = 0
    RevertToPointerRoot = 1
    RevertToParent      = 2

# int XSetInputFocus(Display *display, Window focus, int revert_to, Time time);
xlib.XSetInputFocus.argtypes = display_p, Window, ctypes.c_int, Time

# X.h
KeySym = XID
KeyCode = ctypes.c_ubyte
keycode_p = byte_p

# Xlib.h
class ModifierKeymap(ctypes.Structure):
    _fields_ = [
            ('max_keypermod', ctypes.c_int),
            ('modifiermap', keycode_p),
            ]
modifierkeymap_p = ctypes.POINTER(ModifierKeymap)

# int XDisplayKeycodes(Display *display, int *min_keycodes_return, int *max_keycodes_return);
xlib.XDisplayKeycodes.argtypes = display_p, int_p, int_p

# KeySym *XGetKeyboardMapping(Display *display, KeyCode first_keycode, int keycode_count, int *keysyms_per_keycode_return);
xlib.XGetKeyboardMapping.restype = ctypes.POINTER(KeySym)
xlib.XGetKeyboardMapping.argtypes = display_p, KeyCode, ctypes.c_int, int_p

# XModifierKeymap *XGetModifierMapping(Display *display);
xlib.XGetModifierMapping.restype = modifierkeymap_p
xlib.XGetModifierMapping.argtypes = display_p,

## Keys
NoSymbol = 0
AnyKey = 0

class GrabMode(ctypes.c_int, EnumMixin):
    Sync =  0
    Async = 1

# int XGrabKey(Display *display, int keycode, unsigned int modifiers, Window grab_window, Bool owner_events, int pointer_mode, int keyboard_mode);
#xlib.XGrabKey.argtypes = display_p, ctypes.c_int, KeyModifierMask, Window, Bool, GrabMode, GrabMode
xlib.XGrabKey.argtypes = display_p, KeyCode, GrabKeyModifierMask, Window, Bool, GrabMode, GrabMode

# int XUngrabKey(Display *display, int keycode, unsigned int modifiers, Window grab_window);
#xlib.XUngrabKey.argtypes = display_p, ctypes.c_int, ctypes.c_uint, Window
xlib.XUngrabKey.argtypes = display_p, KeyCode, GrabKeyModifierMask, Window

# char *XKeysymToString(KeySym keysym);
#xlib.XKeysymToString.restype = char_p
#xlib.XKeysymToString.argtypes = KeySym,

# See Xutil.h
class SizeFlags(ctypes.c_long, metaclass=BitmapMetaMaker(ctypes.c_long)):
    _bits_ = [
            ('USPosition',  (1 << 0)),
            ('USSize',      (1 << 1)),
            ('PPosition',   (1 << 2)),
            ('PSize',       (1 << 3)),
            ('PMinSize',    (1 << 4)),
            ('PMaxSize',    (1 << 5)),
            ('PResizeInc',  (1 << 6)),
            ('PAspect',     (1 << 7)),
            ('PBaseSize',   (1 << 8)),
            ('PWinGravity', (1 << 9)),
            ]

class SizeHints(ctypes.Structure):
    class Aspect(ctypes.Structure):
        _fields_= [
                ('x', ctypes.c_int),
                ('y', ctypes.c_int),
                ]
        def __str__(self):
            return '{}({})'.format(self.__class__.__name__, ' '.join('{}={}'.format(name, str(getattr(self, name))) for name, _ in self._fields_))
    _fields_ = [
            ('flags', SizeFlags),
            ('x', ctypes.c_int),
            ('y', ctypes.c_int),
            ('width', ctypes.c_int),
            ('height', ctypes.c_int),
            ('min_width', ctypes.c_int),
            ('min_height', ctypes.c_int),
            ('max_width', ctypes.c_int),
            ('max_height', ctypes.c_int),
            ('width_inc', ctypes.c_int),
            ('height_inc', ctypes.c_int),
            ('min_aspect', Aspect),
            ('max_aspect', Aspect),
            ('base_width', ctypes.c_int),
            ('base_height', ctypes.c_int),
            ('win_gravity', ctypes.c_int),
            ]
    def __str__(self):
        return '{}({})'.format(self.__class__.__name__, ' '.join('{}={}'.format(name, str(getattr(self, name))) for name, _ in self._fields_))

sizehints_p = ctypes.POINTER(SizeHints)

# XSizeHints *XAllocSizeHints(void);
xlib.XAllocSizeHints.restype = sizehints_p
xlib.XAllocSizeHints.argtypes = ctypes.c_void_p,

# Status XGetWMNormalHints(Display *display, Window w, XSizeHints *hints_return, long *supplied_return);
xlib.XGetWMNormalHints.restype = Status
xlib.XGetWMNormalHints.argtypes = display_p, Window, sizehints_p, long_p

class AllowEvents(ctypes.c_int, EnumMixin):
    AsyncPointer    = 0
    SyncPointer     = 1
    ReplayPointer   = 2
    AsyncKeyboard   = 3
    SyncKeyboard    = 4
    ReplayKeyboard  = 5
    AsyncBoth       = 6
    SyncBoth        = 7

# int XAllowEvents(Display *display, int event_mode, Time time);
xlib.XAllowEvents.argtypes = display_p, AllowEvents, Time
