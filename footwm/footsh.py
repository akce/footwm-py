"""
Command line interface for footwm.

Copyright (c) 2016 Jerry Kotland
"""

import argparse

from . import display
from . import ewmh
from . import log as logger
from . import nestedarg
from . import window

log = logger.make(name=__name__)

class FootShell:

    def __init__(self, displayname=None):
        self.display = display.Display(displayname)
        log.debug('%s: connect display=%s', self.__class__.__name__, self.display)
        self.root = window.RootWindow(self.display, self.display.defaultrootwindow)
        self.ewmh = ewmh.EwmhClient(self.display, self.root)

    def activate(self, args):
        """ Activate, bring to front, the window. """
        # XXX Integrate with clientcmd.activatewindow!
        win = self._getwindow(args)
        if win:
            print('activate {}'.format(win))
            self.ewmh.clientmessage('_NET_ACTIVE_WINDOW', win)

    def close(self, args):
        """ Close, delete, the window. """
        win = self._getwindow(args)
        if win:
            # Send a WM_DELETE_WINDOW to the window.
            win.delete()

    def ls(self, args):
        """ List windows. """
        wins = self._getwindowlist(args)
        for i, win in enumerate(wins):
            print('{: 2d} "{}"'.format(i, win.name))

    def _getwindowlist(self, args):
        """ Return window list selected by args. """
        if args.created:
            wins = self.ewmh.clientlist
        else:
            wins = self.ewmh.clientliststacking
        return wins

    def _getwindow(self, args):
        """ Return window selected by args. """
        wins = self._getwindowlist(args)
        win = wins[args.number]
        return win

def make_argparser(footsh):
    winparser = argparse.ArgumentParser(add_help=False)
    winparser.add_argument('--created', default=False, action='store_true', help='windows in creation order. Default: windows in stacking order.')

    parser = argparse.ArgumentParser()
    commands = nestedarg.NestedSubparser(parser.add_subparsers())
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
