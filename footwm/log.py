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

def makehandler(outfilename=None):
    if outfilename:
        h = logging.FileHandler(outfilename)
    else:
        h = logging.StreamHandler()
    return h

def levelnametoint(levelname):
    return getattr(logging, levelname.upper())

def startlogging(modulenames, levelname='info', outfilename=None, logobjname='log'):
    # Note that we don't stop existing logging first. That way we
    # don't stomp on any existing loggers. Must call stoplogging to
    # actually clear.
    h = makehandler(outfilename)
    levelid = levelnametoint(levelname)
    for mod in modulenames:
        logger = make(name=mod, level=levelid, handler=h)
        module = sys.modules[mod]
        setattr(module, logobjname, logger)

def stoplogging():
    h = logging.NullHandler()
    for name, mod in sys.modules.items():
        if hasattr(mod, 'log'):
            # Replace with non-logging version.
            setattr(mod, 'log', make(name=name, handler=h))

def make(name, levelname='error', formatter=None, outfilename=None):
    """ Logging init. Default configuration is for extended traceback information (useful for server) logging. """
    finstance = formatter or logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    log = logging.getLogger(name)
    levelid = levelnametoint(levelname)
    log.setLevel(levelid)
    h = makehandler(outfilename)
    h.setLevel(levelid)
    h.setFormatter(finstance)
    # Python logging module doesn't exactly publish this, but handlers is a list of logging handlers.
    # Doing it this way because the logging API doesn't provide a way to
    # enumerate the existing handlers or erase them!
    # So when we're making the log, replace all handlers with ours.
    log.handlers = [h]
    return log
