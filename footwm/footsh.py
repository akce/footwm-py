"""
Command line interface for footwm.

Copyright (c) 2016 Akce
"""

import argparse

from . import clientcmd
from . import log as logger
from . import nestedarg

log = logger.make(name=__name__)

class FootShell(clientcmd.ClientInitMixin):

    def __init__(self, displayname=None):
        super().__init__(displayname=displayname)
        self.client = clientcmd.ClientCommand(self.display, self.root, self.ewmh)

    def activate(self, args):
        """ Activate, bring to front, the window. """
        self.client.activatewindow(window=args.window, index=args.index, stacking=args.created)

    def close(self, args):
        """ Close, delete, the window. """
        self.client.closewindow(window=args.window, index=args.index, stacking=args.created)

    def ls(self, args):
        """ List windows. """
        wins = self.client.getwindowlist(stacking=args.created)
        for i, win in enumerate(wins):
            print('{: 2d} "{}"'.format(i, win.name))

    def desktops(self, args):
        """ List desktops. """
        if args.names:
            print("setting desktop names: {}".format(args.names))
        else:
            names = self.client.getdesktopnames()
            for i, name in enumerate(names):
                print('{: 2d} "{}"'.format(i, name))

def make_argparser(footsh):
    winparser = argparse.ArgumentParser(add_help=False)
    winparser.add_argument('--created', default=False, action='store_true', help='windows in creation order. Default: windows in stacking order.')

    parser = argparse.ArgumentParser()
    commands = nestedarg.NestedSubparser(parser.add_subparsers())
    with commands('desktops', parents=[winparser], help='desktops') as c:
        c.set_defaults(command=footsh.desktops)
        c.add_argument('names', nargs='*', help='set desktop names')
    with commands('ls', parents=[winparser], help='list windows') as c:
        c.set_defaults(command=footsh.ls)
    with commands('activate', parents=[winparser], aliases=['a'], help='activate window') as c:
        c.set_defaults(command=footsh.activate)
        c.add_argument('number', type=int, default=1, help='index of window to use')
    with commands('close', parents=[winparser], aliases=['c', 'x'], help='close window') as c:
        c.set_defaults(command=footsh.close)
        c.add_argument('number', type=int, default=1, help='index of window to use')
    return parser

def main():
    fs = FootShell()
    parser = make_argparser(fs)
    args = parser.parse_args()
    args.command(args)
