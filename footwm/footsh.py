"""
Command line interface for footwm.

Copyright (c) 2016 Akce
"""

import argparse

from . import clientcmd
from . import log as logger
from . import nestedarg

log = logger.make(name=__name__)

class FootShell:

    def __init__(self, displayname=None):
        display, root = clientcmd.makedisplayroot(displayname)
        self.client = clientcmd.ClientCommand(root)

    def window_activate(self, args):
        """ Activate, bring to front, the window. """
        self.client.activatewindow(index=args.index, stacking=not args.created)

    def window_close(self, args):
        """ Close, delete, the window. """
        self.client.closewindow(index=args.index, stacking=not args.created)

    def window_ls(self, args):
        """ List windows. """
        wins = self.client.getwindowlist(stacking=not args.created)
        for i, win in enumerate(wins):
            print('{: 2d} "{}"'.format(i, win.name))

    def window_mv(self, args):
        """ Move window to a different desktop. """
        self.client.setwindowdesktop(desktopindex=args.desktop, index=args.window, stacking=not args.created)

    def desktop_ls(self, args):
        """ List desktops. """
        names = self.client.getdesktopnames()
        for i, name in enumerate(names):
            print('{: 2d} "{}"'.format(i, name))

    def desktop_add(self, args):
        self.client.adddesktop(name=args.name, index=args.index)

    def desktop_delete(self, args):
        self.client.deletedesktop(index=args.index)

    def desktop_rename(self, args):
        self.client.renamedesktop(name=args.name, index=args.index)

    def desktop_select(self, args):
        self.client.selectdesktop(index=args.index)

    def logging_start(self, args):
        modnames = [m if m.startswith('footwm.') else 'footwm.{}'.format(m) for m in args.modules]
        self.client.startlogging(modulenames=modnames, levelname=args.level, outfilename=args.logfile)

    def logging_stop(self, args):
        self.client.stoplogging()

def make_argparser(footsh):
    winparser = argparse.ArgumentParser(add_help=False)
    winparser.add_argument('--created', default=False, action='store_true', help='windows in creation order. Default: windows in stacking order.')

    parser = argparse.ArgumentParser()
    commands = nestedarg.NestedSubparser(parser.add_subparsers())
    with commands('desktops', aliases=['d', 'desk'], parents=[winparser], help='desktops') as c:
        desks = nestedarg.NestedSubparser(c.add_subparsers())
        with desks('ls', parents=[winparser], help='list desktops') as deskls:
            deskls.set_defaults(command=footsh.desktop_ls)
        with desks('add', aliases=['a'], help='Add a desktop') as deskadd:
            deskadd.add_argument('name', help='Name of desktop. Name must be unique.')
            deskadd.add_argument('--index', type=int, default=0, help='0 based index to insert desktop. Current desktop is always 0 so setting to non-zero will create the desktop, but not select it. Default: %(default)s')
            deskadd.set_defaults(command=footsh.desktop_add)
        with desks('delete', aliases=['d', 'del', 'rm'], parents=[winparser], help='remove desktop') as deskdel:
            deskdel.add_argument('index', type=int, default=0, help='0 based index of desktop to delete. Windows will be moved to the Unassigned group. Default: %(default)s')
            deskdel.set_defaults(command=footsh.desktop_delete)
        with desks('rename', aliases=['r', 'ren'], parents=[winparser], help='rename desktop') as deskren:
            deskren.add_argument('index', type=int, default=0, help='0 based index of desktop to rename. Default: %(default)s')
            deskren.add_argument('name', help='Name of desktop. Name must be unique.')
            deskren.set_defaults(command=footsh.desktop_rename)
        with desks('select', aliases=['s', 'sel'], parents=[winparser], help='select desktop') as desksel:
            desksel.add_argument('index', type=int, default=0, help='0 based index of desktop to select')
            desksel.set_defaults(command=footsh.desktop_select)
    with commands('log', aliases=['l'], help='debugging and logging') as c:
        lconf = nestedarg.NestedSubparser(c.add_subparsers())
        with lconf('start', aliases=['a', 's'], help='Start logging module(s)') as lstart:
            lstart.add_argument('--logfile', default='/tmp/footwm.log', help='output file. Default: %(default)s')
            lstart.add_argument('--level', choices=['debug', 'info', 'error', 'warning'], default='debug', help='log level. Default: %(default)s')
            lstart.add_argument('modules', nargs='+', help='module(s) to debug. Omit the leading footwm. eg, Use only desktop window textui.listbox.')
            lstart.set_defaults(command=footsh.logging_start)
        with lconf('stop', aliases=['r'], help='Stop logging module(s)') as lstop:
            lstop.add_argument('name', nargs='*', help='module(s) to stop logging. Leave empty to stop all logging.')
            lstop.set_defaults(command=footsh.logging_stop)
    with commands('windows', aliases=['w', 'win'], help='windows') as c:
        wins = nestedarg.NestedSubparser(c.add_subparsers())
        with wins('ls', parents=[winparser], help='list windows') as winls:
            winls.set_defaults(command=footsh.window_ls)
        with wins('activate', parents=[winparser], aliases=['a'], help='activate window') as winact:
            winact.set_defaults(command=footsh.window_activate)
            winact.add_argument('index', type=int, default=1, help='index of window to use')
        with wins('close', parents=[winparser], aliases=['c', 'x'], help='close window') as winclose:
            winclose.set_defaults(command=footsh.window_close)
            winclose.add_argument('index', type=int, default=1, help='index of window to use')
        with wins('move', parents=[winparser], aliases=['m', 'mv'], help='move window to desktop') as winmv:
            winmv.set_defaults(command=footsh.window_mv)
            winmv.add_argument('desktop', type=int, help='index of desktop to move to. Default: %(default)s')
            winmv.add_argument('--window', type=int, default=0, help='index of window to move. Default: %(default)s')
    return parser

def main():
    fs = FootShell()
    parser = make_argparser(fs)
    args = parser.parse_args()
    args.command(args)
