"""
App runner.

Copyright (c) 2016 Akce
"""
# Python standard modules.
import shlex
import signal
import subprocess

# Local modules.

class Runner:

    def __init__(self, cwd=None, env=None, shell=False):
        self._cwd = cwd
        self._env = env
        self._shell = shell
        # Don't capture anything for now. Future versions could log to separate files etc.
        self._stdin = subprocess.DEVNULL
        self._stdout = subprocess.DEVNULL
        self._stderr = subprocess.DEVNULL
        # Set action to ignore to stop the OS from creating a zombie process.
        # NOTE Setting the global signal handler here in the
        # constructor has a bad smell, it should really go in a module
        # init function or make Runner a Singleton. But this is a
        # simple app that will only ever create one instance of Runner
        # so leaving here.
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    def run(self, cmdline, **kwargs):
        """ Run cmdline through subprocess, without shell. """
        kwargs = {
                'cwd': kwargs.get('cwd', self._cwd),
                'env': kwargs.get('env', self._env),
                'shell': kwargs.get('shell', self._shell),
                'stdin': kwargs.get('stdin', self._stdin),
                'stdout': kwargs.get('stdout', self._stdout),
                'stderr': kwargs.get('stderr', self._stderr),
            }
        subprocess.Popen(shlex.split(cmdline), **kwargs)
