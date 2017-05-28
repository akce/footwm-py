"""
Watch for Signals.
"""
import fcntl
import os
import signal
import struct

from . import log as logger

log = logger.make(name=__name__)

class SignalsWatch:

    def __init__(self, callback):
        self.callback = callback
        self.pr, self.pw = os.pipe()
        fcntl.fcntl(self.pw, fcntl.F_SETFL, fcntl.fcntl(self.pw, fcntl.F_GETFL, 0) | os.O_NONBLOCK)
        signal.set_wakeup_fd(self.pw)

    def fileno(self):
        """ For select.select. """
        return self.pr

    # Compat with XWatch
    def flush(self):
        pass

    def dispatchevent(self):
        signum = ord(os.read(self.pr, 1))
        log.debug('dispatchevent called for signal %d', signum)
        try:
            self.callback.handle_signal(signum)
        except AttributeError:
            log.error('SignalsWatch.callback handle_signal undefined %s', signum)
