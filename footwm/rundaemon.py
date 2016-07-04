"""
App running daemon.

Copyright (c) 2016 Akce
"""
# Python standard modules.
import subprocess
import threading

# Local modules.
from . import jsonrpc
from . import selectloop

def start(args):
    """ Start a footrun daemon instance. """
    d = Daemon()
    d.serve_forever()

class Daemon:

    def __init__(self):
        pass

    def serve_forever(self):
        pass

    def ls(self):
        """ enumerate our running processes. """
        pass

    def stop(self):
        pass

    def exe(self, cmdlist):
        """ Run args through subprocess, without shell. """
        pass

    def shell(self, cmdlist):
        """ Run args through a subprocess shell instance. """
        pass
