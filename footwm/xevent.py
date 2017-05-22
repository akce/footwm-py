"""
Simple xevent generator.

Copyright (c) 2016 Akce
"""
from . import log as logger
from . import xlib

log = logger.make(name=__name__)

def run(watcher, logfilename):
    # Setup a local logger that is always available so that we can catch unhandled exceptions.
    elog = logger.make(name='applog', levelname='error', outfilename=logfilename)
    while True:
        try:
            watcher.dispatchevent()
        except Exception as e:
            elog.exception(e)

class XWatch:

    def __init__(self, display, root, callback):
        self.display = display
        self.root = root
        self.callback = callback
        self.eventhandlers = {
                xlib.EventName.ClientMessage:       self.handle_clientmessage,
                xlib.EventName.CreateNotify:        self.handle_createnotify,
                xlib.EventName.ConfigureNotify:     self.handle_configurenotify,
                xlib.EventName.ConfigureRequest:    self.handle_configurerequest,
                xlib.EventName.DestroyNotify:       self.handle_destroynotify,
                xlib.EventName.EnterNotify:         self.handle_enternotify,
                xlib.EventName.FocusIn:             self.handle_focusin,
                xlib.EventName.FocusOut:            self.handle_focusout,
                xlib.EventName.KeyPress:            self.handle_keypress,
                xlib.EventName.MapNotify:           self.handle_mapnotify,
                xlib.EventName.MapRequest:          self.handle_maprequest,
                xlib.EventName.MappingNotify:       self.handle_mappingnotify,
                xlib.EventName.PropertyNotify:      self.handle_propertynotify,
                xlib.EventName.UnmapNotify:         self.handle_unmapnotify,
            }

    def fileno(self):
        """ For select.select. """
        return self.display.fileno()

    def dispatchevent(self):
        event = self.display.nextevent
        e = xlib.EventName(event.type)
        log.debug('event: %s', e)
        try:
            handler = self.eventhandlers[e.value]
            handler(event)
        except KeyError:
            log.warn('XWatch unhandled event %s', e)
        except AttributeError:
            log.warn('XWatch.callback unhandled event %s', e)

    def handle_clientmessage(self, event):
        e = event.xclient
        try:
            msg = self.display.atom[e.message_type]
        except KeyError:
            msg = self.display.getatomname(e.message_type)
        log.debug('0x%08x: handle_clientmessage msgid=%d name=%s', e.window, e.message_type, msg)
        self.callback.handle_clientmessage(e)

    def handle_createnotify(self, event):
        # New window has been created.
        e = event.xcreatewindow
        log.debug('0x%08x: CreateNotify parent=0x%08x override_redirect=%s', e.window, e.parent, e.override_redirect)
        self.callback.handle_createnotify(e)

    def handle_configurenotify(self, event):
        # The X server has moved and/or resized window e.window
        e = event.xconfigure
        log.debug('0x%08x: ConfigureNotify event=0x%08x', e.window, e.event)
        self.callback.handle_configurenotify(e)

    def handle_configurerequest(self, event):
        # Some other client tried to reconfigure e.window
        e = event.xconfigurerequest
        log.debug('0x%08x: ConfigureRequest %s', e.window, e.value_mask)
        self.callback.handle_configurerequest(e)

    def handle_destroynotify(self, event):
        # Window has been destroyed.
        e = event.xdestroywindow
        log.debug('0x%08x: DestroyNotify event=0x%08x', e.window, e.event)
        self.callback.handle_destroynotify(e)

    def handle_enternotify(self, event):
        #e = event.xcrossing
        log.debug('0x%08x: EnterNotify', event.xany.window)
        self.callback.handle_enternotify(event.xany)

    def handle_focusin(self, event):
        e = event.xfocus
        log.debug('0x%08x: focusin mode=%s detail=%s', e.window, e.mode, e.detail)
        self.callback.handle_focusin(e)

    def handle_focusout(self, event):
        e = event.xfocus
        log.debug('0x%08x: focusout mode=%s detail=%s', e.window, e.mode, e.detail)
        self.callback.handle_focusout(e)

    def handle_keypress(self, event):
        e = event.xkey
        log.debug('0x%08x: handle_keypress keycode=0x%x modifiers=%s', e.window, e.keycode, e.state.value)
        self.callback.handle_keypress(e)

    def handle_mapnotify(self, event):
        # Server has displayed the window.
        e = event.xmap
        log.debug('0x%08x: MapNotify event=0x%08x override_redirect=%s', e.window, e.event, e.override_redirect)
        self.callback.handle_mapnotify(e)

    def handle_maprequest(self, event):
        # A window has requested that it be shown.
        e = event.xmaprequest
        log.debug('0x%08x: MapRequest', e.window)
        self.callback.handle_maprequest(e)

    def handle_mappingnotify(self, event):
        self.callback.handle_mappingnotify(event)

    def handle_propertynotify(self, event):
        e = event.xproperty
        for k, v in self.display.atom.items():
            if v == e.atom:
                atomname = k
                break
        else:
            atomname = None
        log.debug('0x%08x: PropertyNotify %s:%d send_event=%s', e.window, atomname, e.atom, e.send_event)
        self.callback.handle_propertynotify(e, atomname)

    def handle_unmapnotify(self, event):
        e = event.xunmap
        log.debug('0x%08x: UnmapNotify', e.window)
        self.callback.handle_unmapnotify(e)
