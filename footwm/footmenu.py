""" Foot menu. """

# Python standard modules.
import argparse
import curses

# Local modules.
from . import clientcmd
from . import nestedarg
from .textui import listbox
from .textui import screen

def xinit(displayname=None):
    display, root = clientcmd.makedisplayroot(displayname)
    client = clientcmd.ClientCommand(root)
    return client, display, root

class WindowApp:

    def __init__(self, client, showfirst):
        offset = 0 if showfirst else 1
        self.client = client
        self.windows = self.client.getwindowlist()[offset:]
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

    def _initview(self):
        self.scr.init()
        self.model = listbox.Model(contents=[w.name for w in self.windows])
        self.listbox = listbox.ListBox(self.scr)
        self.listbox.contents = self.model
        self.scr.windows = [self.listbox]
        self.scr.draw()

    def run(self):
        self._initview()
        self.scr.run()

    def stop(self):
        self.scr.running = False

    def up(self):
        self.listbox.up()

    def down(self):
        self.listbox.down()

    def pageup(self):
        self.listbox.pageup()

    def pagedown(self):
        self.listbox.pagedown()

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

    def activateselection(self):
        win = self.windows[self.listbox.selected]
        self.client.activatewindow(window=win.window)
        self.stop()

    def closeselection(self):
        win = self.windows[self.listbox.selected]
        self.client.closewindow(window=win.window)
        self.stop()

def windowmenu(args):
    client, display, root = xinit(displayname=args.displayname)
    app = WindowApp(client, showfirst=args.showfirst)
    try:
        app.run()
    finally:
        app.close()

def desktopmenu(args):
    pass

def parse_args():
    dispparser = argparse.ArgumentParser(add_help=False)
    dispparser.add_argument('--displayname', help='X display name.')
    dispparser.add_argument('--showfirst', default=False, action='store_true', help='Show first list entry')

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
