""" Foot menu. """

# Python standard modules.
import argparse
import curses
import time

# Local modules.
from . import clientcmd
from . import nestedarg
from .textui import listbox
from .textui import msgwin
from .textui import screen

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
        # Command mode keymap.
        self.eventmap = {
            ord('a'):		self.activateselection,
            ord('c'):		self.closeselection,
            ord('q'):		self.stop,
            10:			self.activateselection,
            curses.KEY_UP:	self.up,
            ord('k'):		self.up,
            curses.KEY_DOWN:	self.down,
            ord('j'):		self.down,
            curses.KEY_PPAGE:	self.pageup,
            ord('K'):		self.pageup,
            curses.KEY_NPAGE:	self.pagedown,
            ord('J'):		self.pagedown,
            }

    def run(self):
        self.scr.init()
        self._model = self._makemodel()
        self._model.attachview(listbox.ListBox(model=self._model, parent=self.scr))
        self.scr.windows = self._model.views[:]
        self.scr.draw()
        self.scr.run()

    def stop(self):
        self.scr.running = False

    def up(self):
        self._model.up()

    def down(self):
        self._model.down()

    def pageup(self):
        self._model.pageup()

    def pagedown(self):
        self._model.pagedown()

    def close(self):
        self.scr.close()

    def on_user_event(self, kid):
        try:
            func = self.eventmap[kid]
        except KeyError:
            pass
        else:
            func()
            self.scr.draw()

class DesktopApp(AppMixin):

    def __init__(self, client, showcurrent, msgduration=1.2):
        super().__init__(client, showcurrent, msgduration)

    def _makemodel(self):
        desktops = self.client.getdesktopnames()[self._offset:]
        columns = [listbox.ListColumn(name='desk', label="Desktop"),
                   listbox.ListColumn(name='desknum', visible=False, label="Number"),
            ]
        return listbox.Model(columns=columns, rows=[{'desk': d, 'desknum': i} for i, d in enumerate(desktops)])

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
        return listbox.Model(rows=[{'res': w.resourcename, 'cls': w.resourceclass, 'title': w.name, 'wid': w.window} for w in windows], columns=columns)

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

    parser = argparse.ArgumentParser()
    commands = nestedarg.NestedSubparser(parser.add_subparsers())
    with commands('windows', aliases=['w', 'win'], parents=[dispparser], help='windows only menu') as c:
        c.set_defaults(command=windowmenu)
    with commands('desktops', aliases=['d', 'desk'], parents=[dispparser], help='desktops only menu') as c:
        c.set_defaults(command=desktopmenu)
    return parser.parse_args()

def main():
    args = parse_args()
    args.command(args)
