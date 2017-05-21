"""
Default logging setup.

Copyright (c) 2014-2016 Akce
"""
# Python standard modules.
import logging
import sys

def addargs(parser):
    parser.add_argument('--logmodules', nargs='+', default=[], help='list of package.module names.')
    parser.add_argument('--loglevel', choices=['debug', 'info', 'warn', 'error', 'critical'], default='debug', help='comma separated list of package.module names. eg, footwm.display,footwm.ewmh')
    parser.add_argument('--logfile', help='Write log messages to this file. Default: stdout')

def startlogging(modulenames, levelname='info', outfilename=None):
    # XXX Should we stop existing logging first?
    if outfilename:
        h = logging.FileHandler(outfilename)
    else:
        h = logging.StreamHandler()
    for mod in modulenames:
        lvl = getattr(logging, levelname.upper())
        logger = make(name=mod, level=lvl, handler=h)
        module = sys.modules[mod]
        setattr(module, 'log', logger)

def stoplogging():
    h = logging.NullHandler()
    for name, mod in sys.modules.items():
        if hasattr(mod, 'log'):
            # Replace with non-logging version.
            setattr(mod, 'log', make(name=name, handler=h))

def make(name, level=logging.WARNING, formatter=None, handler=None):
    """ Logging init. Default configuration is for extended traceback information (useful for server) logging. """
    finstance = formatter or logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    log = logging.getLogger(name)
    log.setLevel(level)
    if handler is None:
        h = logging.StreamHandler()
    else:
        h = handler
    h.setLevel(level)
    h.setFormatter(finstance)
    # Python logging module doesn't exactly publish this, but handlers is a list of logging handlers.
    # Doing it this way because the logging API doesn't provide a way to
    # enumerate the existing handlers or erase them!
    # So when we're making the log, replace all handlers with ours.
    log.handlers = [h]
    return log
