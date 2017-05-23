"""
Main footwm module.

Copyright (c) 2016 Akce
"""

# Python standard modules.
import logging

# Local modules.
from . import desktop
from . import display
from . import window
from . import xevent
from . import xlib
import footwm.log

log = footwm.log.make(name=__name__)

class Foot(object):

    def __init__(self, displayname=None):
        self.display = display.Display(displayname)
        log.debug('%s: connect display=%s', self.__class__.__name__, self.display)
        # TODO: worry about screens, displays, xrandr and xinerama!
        self.root = window.WmRoot(self.display, self.display.defaultrootwindow)
        eventmask = xlib.InputEventMask.PropertyChange |	\
                    xlib.InputEventMask.StructureNotify |	\
                    xlib.InputEventMask.SubstructureRedirect |	\
                    xlib.InputEventMask.SubstructureNotify
        self.display.install(self.root, eventmask)
        # We are now the window manager - continue initialisation.
        log.debug('0x%08x: root %s', self.root.window, self.root)
        # XXX Should we remove WM_ICON_SIZE from root? In case an old WM installed it. See ICCCM 4.1.9
        self.display.logerrors()
        self.xwatch = xevent.XWatch(self.display, self.root, self)
        self._desktop = desktop.Desktop(self.display, self.root)
        self._desktop.redraw()

    def handle_clientmessage(self, e):
        try:
            win = self.root.children[e.window]
        except KeyError:
            win = None
        self._desktop.handle_clientmessage(e.message_type, e, win=win)

    def handle_createnotify(self, e):
        # New window has been created.
        if not e.override_redirect:
            self.root.newchild(e.window)

    def handle_configurenotify(self, e):
        # This block of code resizes the window if it's still not at the ideal geometry.
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

    def handle_configurerequest(self, e):
        # NOTE: Allow all configure requests, even if their dimensions are not what we want.
        # Most clients get slow and behave weird if they don't get their way, so we'll honour all
        # requests but we'll request the dimensions we want in the callback configure notify handler.
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

    def handle_destroynotify(self, destroywindowevent):
        # Only handle if the notify event not caused by a sub-structure redirect.
        if destroywindowevent.event == destroywindowevent.window:
            try:
                win = self.root.children[destroywindowevent.window]
            except KeyError:
                log.debug('0x%08x: not found in root %s', destroywindowevent.window, self.root)
            else:
                self._desktop.unmanagewindow(win)

    def handle_mapnotify(self, mapevent):
        # Only handle if the notify event not caused by a sub-structure redirect.
        if mapevent.event == mapevent.window:
            # Add a WM_STATE property to the window. See ICCCM 4.1.3.1
            try:
                win = self.root.children[mapevent.window]
            except KeyError:
                log.error('0x%08x: window not found, cannot set WM_STATE=Normal', mapevent.window)
            else:
                win.wm_state = xlib.WmStateState.Normal

    def handle_maprequest(self, maprequestevent):
        # A window has requested that it be shown.
        windowid = maprequestevent.window
        try:
            win = self.root.children[windowid]
        except KeyError:
            log.error('0x%08x: MapRequest for unknown window!!!', windowid)
        else:
            self._desktop.managewindow(win)

    def handle_propertynotify(self, propertyevent, atomname):
        """ Property on the root window has changed. """
        self._desktop.handle_propertynotify(propertyevent.atom)

    def handle_unmapnotify(self, unmapevent):
        if unmapevent.send_event:
            # The UnmapNotify is because client called something like XWithdrawWindow or XIconifyWindow.
            # Unmap the window, but remove when the xserver sends another UnmapNotify message with send_event=False.
            log.debug('0x%08x: Client requests unmap.. calling XUnmapWindow', unmapevent.window)
            self.display.unmapwindow(unmapevent.window)
        else:
            # Only handle if the notify event not caused by a sub-structure redirect. See man XUnmapEvent
            if unmapevent.event == unmapevent.window:
                try:
                    win = self.root.children[unmapevent.window]
                except KeyError:
                    log.error('0x%08x: UnmapRequest for unknown window!!!', unmapevent.window)
                else:
                    self._desktop.withdrawwindow(win=win)

    def __del__(self):
        self.display = None

def parseargs():
    import argparse
    parser = argparse.ArgumentParser()
    footwm.log.addargs(parser)
    args = parser.parse_args()
    footwm.log.startlogging(modulenames=args.logmodules, levelname=args.loglevel, outfilename=args.logfile)

def main():
    parseargs()
    try:
        foot = Foot()
    except Exception as e:
        log.exception(e)
    else:
        # Flush ensures that our x config has been pushed to the server, and then we can receive events on the X socket.
        # Required now since we don't wait on display.nextevent (which calls flush internally).
        foot.xwatch.flush()
        xevent.run(foot.xwatch, logfilename='/tmp/footwmerrors.log')
