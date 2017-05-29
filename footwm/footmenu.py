""" Foot menu. """

# Python standard modules.
import argparse
import os
import time

# Local modules.
from . import clientcmd
from . import nestedarg
from . import selectloop
from . import xevent
from . import xlib
from .textui import keyconfig
from .textui import listbox
from .textui import msgwin
from .textui import screen
from .textui import util

from . import log as logger

log = logger.make(name=__name__)

def xinit(displayname=None):
    display, root = clientcmd.makedisplayroot(displayname)
    display.logerrors()
    client = clientcmd.ClientCommand(root)
    return client, display, root

class AppMixin:

    def __init__(self, client, display, root, skipfirst, msgduration=1.2):
        self.client = client
        self.xwatch = xevent.XWatch(display, root, self)
        self._offset = 1 if skipfirst else 0
        self._msgduration = msgduration
        self.scr = screen.Screen(self)
        self._model = self._makemodel()
        with keyconfig.KeyBuilder(installer=self._installkeymap) as kc:
            kc.addkey('a', self.activateselection)
            kc.addkey('x', self.closeselection)
            kc.addkey('q', self.stop)
            kc.addkey('ESC', self.stop)
            kc.addkey('ENTER', self.activateselection)
            ## Navigation keys.
            kc.addkey('UP', self._model.up)
            kc.addkey('k', self._model.up)
            kc.addkey('DOWN', self._model.down)
            kc.addkey('j', self._model.down)
            kc.addkey('PAGEUP', self._model.pageup)
            kc.addkey('K', self._model.pageup)
            kc.addkey('PAGEDOWN', self._model.pagedown)
            kc.addkey('J', self._model.pagedown)

    def _installkeymap(self, keymap):
        self.eventmap = keymap['root']

    def run(self):
        #log.debug('watch for property changes 0x%08x', xlib.InputEventMask.PropertyChange)
        #root.manage(xlib.InputEventMask.PropertyChange)
        try:
            selfwin = self.client.root.children[int(os.environ['WINDOWID'])]
        except KeyError:
            selfwin = self.client.root.newchild(int(os.environ['WINDOWID']))
        selfwin.manage(xlib.InputEventMask.FocusChange)
        # flush is needed or else the server never sends us events. Normally it's called by nextevent, but we need to do
        # it manually when using select.
        self.xwatch.flush()
        self.scr.init()
        self._model.view = listbox.ListBox(model=self._model, parent=self.scr)
        self.scr.windows = [self._model.view]
        self.exitonempty()
        self.scr.draw()
        # Handle both X and curses events.
        while self.scr.running:
            rs, _, _ = selectloop.select(reads=[self.scr, self.xwatch])
            for r in rs:
                r.dispatchevent()
        self.scr.close()

    def handle_focusout(self, event):
        log.debug('focusout - stop app')
        self.stop()

    def showmessage(self, content, title, parent=None):
        msg = msgwin.Message(lines=content, parent=parent or self.scr, title=title)
        self.scr.windows.append(msg)
        self.scr.draw()
        time.sleep(self._msgduration)
        self.scr.windows.remove(msg)

    def exitonempty(self):
        if len(self._model.rows) == 0:
            self.showmessage(content=['Nothing to do'], title='Exiting..')
            self.stop()

    def stop(self):
        self.scr.running = False

    def close(self):
        self.scr.close()

    def on_user_event(self, keycode):
        try:
            key = self.eventmap[keycode]
        except KeyError:
            pass
        else:
            key.action()
            self.scr.draw()

class DesktopApp(AppMixin):

    def __init__(self, client, display, root, skipfirst, msgduration=1.2):
        super().__init__(client, display, root, skipfirst, msgduration)

    def _makemodel(self):
        desktops = self.client.getdesktopnames()[self._offset:]
        columns = [listbox.ListColumn(name='desk', label="Desktop"),
                   listbox.ListColumn(name='desknum', visible=False, label="Number"),
            ]
        model = listbox.Model(columns=columns, rows=[{'desk': d, 'desknum': i} for i, d in enumerate(desktops, self._offset)])
        model.selectedindex = self.client.currentdesktop
        return model

    def activateselection(self):
        row = self._model.selected
        deskname = row['desk']
        desknum = int(row['desknum'])
        self.showmessage(content=[deskname], title='Selecting')
        self.client.selectdesktop(desknum)
        self.scr.draw()
        self.stop()

    def closeselection(self):
        row = self._model.selected
        desknum = row['desknum']
        self.client.deletedesktop(desknum)
        self.stop()

class WindowApp(AppMixin):

    def __init__(self, client, display, root, skipfirst, msgduration=1.2):
        super().__init__(client, display, root, skipfirst, msgduration)

    def _makemodel(self):
        # Ignore window that houses footmenu.
        # FIXME: call client.getwindowlist first so it initialises all root.children windows. Then client.activewindow will exist.
        allwindows = self.client.getwindowlist()
        selfwin = self.client.root.children[int(os.environ['WINDOWID'])]
        currentwin = self.client.activewindow
        currentset = frozenset([selfwin, currentwin])
        windows = [w for w in allwindows if w not in currentset][self._offset:]
        columns = [
            listbox.ListColumn(name='win', label='Window', visible=True, renderer=lambda x: '0x{:08x}'.format(x.window)),
            listbox.ListColumn(name='res', label='Resource'),
            listbox.ListColumn(name='cls', label='Class'),
            listbox.ListColumn(name='host', label='Host'),
            listbox.ListColumn(name='title', label='Title'),
            ]
        model = listbox.Model(rows=[{'res': w.resourcename, 'cls': w.resourceclass, 'host': w.clientmachine, 'title': w.name, 'win': w} for w in windows], columns=columns)
        aw = self.client.activewindow
        for i, w in enumerate(windows):
            if w.window == aw.window:
                break
        else:
            i = 0
        model.selectedindex = i
        return model

    def activateselection(self):
        row = self._model.selected
        winname = row['title']
        win = row['win']
        self.showmessage(content=[winname], title='Activating')
        self.client.activatewindow(window=win.window)
        self.scr.draw()
        self.stop()

    def closeselection(self):
        row = self._model.selected
        wid = row['win'].window
        self.client.closewindow(window=wid)
        self.stop()

    def handle_propertynotify(self, propertyevent, atomname):
        log.debug('propertynotify %s', atomname)

def windowmenu(args):
    client, display, root = xinit(displayname=args.displayname)
    app = WindowApp(client, display, root, skipfirst=args.skipfirst, msgduration=args.msgduration)
    try:
        app.run()
    finally:
        app.close()

def desktopmenu(args):
    client, display, root = xinit(displayname=args.displayname)
    app = DesktopApp(client, display, root, skipfirst=args.skipfirst, msgduration=args.msgduration)
    try:
        app.run()
    finally:
        app.close()

def parse_args():
    dispparser = argparse.ArgumentParser(add_help=False)
    dispparser.add_argument('--displayname', help='X display name.')
    dispparser.add_argument('--msgduration', default=1.2, type=float, help='Seconds to show message window before actioning')
    dispparser.add_argument('--skipfirst', default=False, action='store_true', help='Skip first entry in window/desktop list. Default: %(default)s')
    dispparser.add_argument('--escapedelay', default=25, type=int, help='Set curses escape delay')

    parser = argparse.ArgumentParser()
    logger.addargs(parser)
    commands = nestedarg.NestedSubparser(parser.add_subparsers())
    with commands('windows', aliases=['w', 'win'], parents=[dispparser], help='windows only menu') as c:
        c.set_defaults(command=windowmenu)
    with commands('desktops', aliases=['d', 'desk'], parents=[dispparser], help='desktops only menu') as c:
        c.set_defaults(command=desktopmenu)
    return parser.parse_args()

def main():
    args = parse_args()
    footmods = [m if m.startswith('footwm.') else 'footwm.{}'.format(m) for m in args.logmodules]
    logger.startlogging(footmods, levelname=args.loglevel, outfilename=args.logfile)
    util.setescapedelay(args.escapedelay)
    args.command(args)
