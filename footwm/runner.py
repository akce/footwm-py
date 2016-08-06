"""
App runner.

Copyright (c) 2016 Akce
"""
# Python standard modules.
import shlex
import subprocess
import threading

# Local modules.
from . import log as loghelp

log = loghelp.make(name=__name__)

class App(threading.Thread):

    def run(self):
        cmdline, = self._args
        p = subprocess.Popen(shlex.split(cmdline), **self._kwargs)
        retcode = p.wait()
        log.debug('process returned=%d', retcode)

class Runner:

    def __init__(self, cwd=None, env=None, shell=False):
        self._id = 1
        self._cwd = cwd
        self._env = env
        self._shell = shell
        # Don't capture anything for now. Future versions could log to separate files etc.
        self._stdin = subprocess.DEVNULL
        self._stdout = subprocess.DEVNULL
        self._stderr = subprocess.DEVNULL

    def run(self, cmdline, **kwargs):
        """ Run cmdline through subprocess, without shell. """
        name = 'runner-{}'.format(self._id)
        self._id += 1
        args = cmdline,
        kwargs = {
                'cwd': kwargs.get('cwd', self._cwd),
                'env': kwargs.get('env', self._env),
                'shell': kwargs.get('shell', self._shell),
                'stdin': kwargs.get('stdin', self._stdin),
                'stdout': kwargs.get('stdout', self._stdout),
                'stderr': kwargs.get('stderr', self._stderr),
            }
        app = App(name=name, daemon=False, args=args, kwargs=kwargs)
        app.start()
