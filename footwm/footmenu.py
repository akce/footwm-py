""" Foot menu. """

# Python standard modules.
import argparse
import time

# Local modules.
from . import clientcmd
from . import nestedarg
from .textui import keyconfig
from .textui import listbox
from .textui import msgwin
from .textui import screen
from .textui import util

def xinit(displayname=None):
    display, root = clientcmd.makedisplayroot(displayname)
    client = clientcmd.ClientCommand(root)
    return client, display, root

class AppMixin:

    def __init__(self, client, showcurrent, msgduration=1.2):
        self.client = client
        self._offset = 0 if showcurrent else 1
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
        self.scr.init()
        self._model.view = listbox.ListBox(model=self._model, parent=self.scr)
        self.scr.windows = [self._model.view]
        self.scr.draw()
        self.scr.run()

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

    def __init__(self, client, showcurrent, msgduration=1.2):
        super().__init__(client, showcurrent, msgduration)

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
        desknum = row['desknum']
        msg = msgwin.Message(lines=[deskname], parent=self.scr, title='Selecting')
        self.scr.windows.append(msg)
        self.scr.draw()
        time.sleep(self._msgduration)
        self.scr.windows.remove(msg)
        self.client.selectdesktop(desknum)
        self.scr.draw()
        self.stop()

    def closeselection(self):
        row = self._model.selected
        desknum = row['desknum']
        self.client.deletedesktop(desknum)
        self.stop()

class WindowApp(AppMixin):

    def __init__(self, client, showcurrent, msgduration=1.2):
        super().__init__(client, showcurrent, msgduration)

    def _makemodel(self):
        windows = self.client.getwindowlist()[self._offset:]
        columns = [listbox.ListColumn(name='res', label='Resource'),
                   listbox.ListColumn(name='cls', label='Class'),
                   listbox.ListColumn(name='title', label='Title'),
                   listbox.ListColumn(name='wid', label='Window', visible=False),
            ]
        model = listbox.Model(rows=[{'res': w.resourcename, 'cls': w.resourceclass, 'title': w.name, 'wid': w.window} for w in windows], columns=columns)
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
        wid = row['wid']
        msg = msgwin.Message(lines=[winname], parent=self.scr, title='Activating')
        self.scr.windows.append(msg)
        self.scr.draw()
        time.sleep(self._msgduration)
        self.scr.windows.remove(msg)
        self.client.activatewindow(window=wid)
        self.scr.draw()
        self.stop()

    def closeselection(self):
        row = self._model.selected
        wid = row['wid']
        self.client.closewindow(window=wid)
        self.stop()

def windowmenu(args):
    client, display, root = xinit(displayname=args.displayname)
    app = WindowApp(client, showcurrent=args.showcurrent, msgduration=args.msgduration)
    try:
        app.run()
    finally:
        app.close()

def desktopmenu(args):
    client, display, root = xinit(displayname=args.displayname)
    app = DesktopApp(client, showcurrent=args.showcurrent, msgduration=args.msgduration)
    try:
        app.run()
    finally:
        app.close()

def parse_args():
    dispparser = argparse.ArgumentParser(add_help=False)
    dispparser.add_argument('--displayname', help='X display name.')
    dispparser.add_argument('--msgduration', default=1.2, type=float, help='Seconds to show message window before actioning')
    dispparser.add_argument('--showcurrent', default=False, action='store_true', help='Show current desktop/window')
    dispparser.add_argument('--escapedelay', default=25, type=int, help='Set curses escape delay')

    parser = argparse.ArgumentParser()
    commands = nestedarg.NestedSubparser(parser.add_subparsers())
    with commands('windows', aliases=['w', 'win'], parents=[dispparser], help='windows only menu') as c:
        c.set_defaults(command=windowmenu)
    with commands('desktops', aliases=['d', 'desk'], parents=[dispparser], help='desktops only menu') as c:
        c.set_defaults(command=desktopmenu)
    return parser.parse_args()

def main():
    args = parse_args()
    util.setescapedelay(args.escapedelay)
    args.command(args)
