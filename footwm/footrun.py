"""
App running module for footwm.

Copyright (c) 2016 Akce
"""
# Python standard modules.
import argparse

# Local modules.
from . import log as loghelp
from . import nestedarg
from . import rundaemon
from . import runclient

log = loghelp.make(name=__name__)

def daemonstart(args):
    rundaemon.start(args)

def daemonls(args):
    runclient.ls(args)

def daemonstop(args):
    runclient.stop(args)

def exe(args):
    runclient.exe(cmdlist=args.args)

def shell(args):
    runclient.shell(cmdlist=args.args)

def makeargparser():
    parser = argparse.ArgumentParser()
    commands = nestedarg.NestedSubparser(parser.add_subparsers())
    with commands('daemon', aliases=['d'], help='app running daemon commands') as c:
        d = nestedarg.NestedSubparser(c.add_subparsers())
        with d('start', help='start a footrun daemon') as d1:
            d1.set_defaults(command=daemonstart)
        with d('stop', help='stop a footrun daemon') as d1:
            d1.set_defaults(command=daemonstop)
        with d('ls', help='list running processes') as d1:
            d1.set_defaults(command=daemonls)
    with commands('exec', aliases=['e'], help='exec (without shell) a command') as c:
        c.set_defaults(command=exe)
        # TODO specify command output logging options.
        c.add_argument('args', nargs='+', help='command line arguments of command')
    with commands('shell', aliases=['sh'], help='run a command through the shell') as c:
        c.set_defaults(command=shell)
        # TODO specify command output logging options.
        c.add_argument('args', nargs='+', help='command line arguments of command')
    return parser

def main():
    parser = makeargparser()
    args = parser.parse_args()
    args.command(args)
