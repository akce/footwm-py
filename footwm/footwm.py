"""
Main footwm module.

Copyright (c) 2016 Akce
"""

# Python standard modules.
import logging

# Local modules.
from . import xlib
from . import desktop
from . import display
from . import window
from . import xevent
import footwm.log

log = footwm.log.make(name=__name__)

class Foot(object):

    def __init__(self, displayname=None):
        self.display = display.Display(displayname)
        log.debug('%s: connect display=%s', self.__class__.__name__, self.display)
        # TODO: worry about screens, displays, xrandr and xinerama!
        self.root = window.RootWindow(self.display, self.display.defaultrootwindow)
        eventmask = xlib.InputEventMask.StructureNotify | xlib.InputEventMask.SubstructureRedirect | xlib.InputEventMask.SubstructureNotify
        self.display.install(self.root, eventmask)
        # We are now the window manager - continue initialisation.
        log.debug('0x%08x: root %s', self.root.window, self.root)
        # XXX Should we remove WM_ICON_SIZE from root? In case an old WM installed it. See ICCCM 4.1.9
        def xerrorhandler(display, xerrorevent):
            log.error('X Error: %s', xerrorevent)
            return 0
        self.display.errorhandler = xerrorhandler
        self._makehandlers()
        self._desktop = desktop.Desktop(self.display, self.root)
        self._desktop.show()

    def _makehandlers(self):
        self.eventhandlers = {
                xlib.EventName.ClientMessage:       self.handle_clientmessage,
                xlib.EventName.CreateNotify:        self.handle_createnotify,
                xlib.EventName.ConfigureNotify:     self.handle_configurenotify,
                xlib.EventName.ConfigureRequest:    self.handle_configurerequest,
                xlib.EventName.DestroyNotify:       self.handle_destroynotify,
                xlib.EventName.FocusIn:             self.handle_focusin,
                xlib.EventName.FocusOut:            self.handle_focusout,
                xlib.EventName.MapNotify:           self.handle_mapnotify,
                xlib.EventName.MapRequest:          self.handle_maprequest,
                xlib.EventName.UnmapNotify:         self.handle_unmapnotify,
                }

    def noop(self, event):
        log.debug('noop %s', xlib.EventName(event.type))

    def handle_clientmessage(self, event):
        e = event.xclient
        try:
            msg = self.display.atom[e.message_type]
        except KeyError:
            msg = self.display.getatomname(e.message_type)
        log.debug('0x%08x: handle_clientmessage msgid=%d name=%s', e.window, e.message_type, msg)
        try:
            win = self.root.children[e.window]
        except KeyError:
            log.error('0x%08x: No window object for client message', e.window)
        else:
            if e.message_type == self.display.atom['_NET_ACTIVE_WINDOW']:
                log.debug('0x%08x: _NET_ACTIVE_WINDOW', e.window)
                self._desktop.show(win=win)
            elif e.message_type == self.display.atom['_NET_CLOSE_WINDOW']:
                win.delete()
                # Do nothing else. We'll receive DestroyNotify etc if the client window is deleted.

    def handle_createnotify(self, event):
        # New window has been created.
        e = event.xcreatewindow
        self.root.newchild(e.window)
        log.debug('0x%08x: CreateNotify parent=0x%08x override_redirect=%s', e.window, e.parent, e.override_redirect)

    def handle_configurenotify(self, event):
        # The X server has moved and/or resized window e.window
        e = event.xconfigure
        # Only handle if the notify event not caused by a sub-structure redirect.
        if e.event == e.window:
            geom = display.Geometry(e)
            log.debug('0x%08x: ConfigureNotify %s', e.window, geom)
            try:
                win = self.root.children[e.window]
            except KeyError:
                pass
            else:
                win.geom = geom
                if win.wantedgeom == geom:
                    log.debug('0x%08x: current dimensions are good, no need to request again', e.window)
                else:
                    # Window is not the size we want, make a configure request.
                    wg = win.wantedgeom
                    log.debug('0x%08x: requesting again, wanted %s current %s', e.window, win.wantedgeom, win.geom)
                    self.display.moveresizewindow(win, wg.x, wg.y, wg.w, wg.h)

    def handle_configurerequest(self, event):
        # Some other client tried to reconfigure e.window
        # NOTE: Allow all configure requests, even if their dimensions are not what we want.
        # Most clients get slow and behave weird if they don't get their way, so we'll honour all
        # requests but we'll request the dimensions we want in the callback configure notify handler.
        e = event.xconfigurerequest
        geom = display.Geometry(e)
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
        requestedgeom = display.Geometry(wc)
        log.debug('0x%08x: requested %s %s', e.window, xlib.ConfigureWindowStructure(changemask), requestedgeom)
        if changemask:
            self.display.configurewindow(e.window, changemask, wc)

    def handle_destroynotify(self, event):
        # Window has been destroyed.
        e = event.xdestroywindow
        # Only handle if the notify event not caused by a sub-structure redirect.
        if e.event == e.window:
            log.debug('0x%08x: DestroyNotify event=0x%08x', e.window, e.event)
            try:
                win = self.root.children[e.window]
            except KeyError:
                log.debug('0x%08x: not found in root %s', e.window, self.root)
            else:
                self._desktop.unmanagewindow(win)

    def handle_focusin(self, event):
        e = event.xfocus
        log.debug('0x%08x: focusin mode=%s detail=%s', e.window, e.mode, e.detail)

    def handle_focusout(self, event):
        e = event.xfocus
        log.debug('0x%08x: focusout mode=%s detail=%s', e.window, e.mode, e.detail)

    def handle_mapnotify(self, event):
        # Server has displayed the window.
        e = event.xmap
        # Only handle if the notify event not caused by a sub-structure redirect.
        if e.event == e.window:
            log.debug('0x%08x: MapNotify event=0x%08x override_redirect=%s', e.window, e.event, e.override_redirect)
            # Add a WM_STATE property to the window. See ICCCM 4.1.3.1
            try:
                win = self.root.children[e.window]
            except KeyError:
                log.error('0x%08x: window not found, cannot set WM_STATE=Normal', e.window)
            else:
                win.wm_state = xlib.WmStateState.Normal

    def handle_maprequest(self, event):
        # A window has requested that it be shown.
        windowid = event.xmaprequest.window
        try:
            win = self.root.children[windowid]
        except KeyError:
            log.error('0x%08x: MapRequest for unknown window!!!', w)
        else:
            self._desktop.managewindow(win)

    def handle_unmapnotify(self, event):
        e = event.xunmap
        if e.send_event:
            # The UnmapNotify is because client called something like XWithdrawWindow or XIconifyWindow.
            # Unmap the window, but remove when the xserver sends another UnmapNotify message with send_event=False.
            log.debug('0x%08x: Client requests unmap.. calling XUnmapWindow', e.window)
            self.display.unmapwindow(e.window)
        else:
            # Only handle if the notify event not caused by a sub-structure redirect. See man XUnmapEvent
            if e.event == e.window:
                try:
                    win = self.root.children[e.window]
                except KeyError:
                    log.error('0x%08x: UnmapRequest for unknown window!!!', e.window)
                else:
                    self._desktop.withdrawwindow(win=win)

    def __del__(self):
        self.display = None

def parseargs():
    import argparse
    parser = argparse.ArgumentParser()
    footwm.log.addargs(parser)
    args = parser.parse_args()
    footwm.log.configlogging(args.logspec, args.outfile)

def main():
    parseargs()
    try:
        foot = Foot()
    except Exception as e:
        log.exception(e)
    else:
        xevent.run(foot.display, foot.eventhandlers)
