"""
Default logging setup.

Copyright (c) 2014-2016 Akce
"""
# Python standard modules.
import logging
import sys

def addargs(parser):
    parser.add_argument('--logspec', help='comma separated list of package.module:loglevel specifiers. eg, footwm.display:debug,footwm.ewmh:info')
    parser.add_argument('--outfile', help='Write log messages to this file. Default: stdout')

def configlogging(logspec, outfilename=None):
    # Configure a filehandler if given an outfilename.
    if outfilename:
        h = logging.FileHandler(outfilename)
    else:
        h = logging.StreamHandler()
    mods = logspec.split(',')
    for m in mods:
        try:
            mod, lvlname = m.split(':')
        except ValueError:
            mod = m
            # Default to INFO level logging if the module is present.
            lvlname = 'info'
        lvl = getattr(logging, lvlname.upper())
        logger = make(name=mod, level=lvl, handler=h)
        module = sys.modules[mod]
        setattr(module, 'log', logger)

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
