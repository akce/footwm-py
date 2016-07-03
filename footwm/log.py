"""
Default logging setup.

Copyright (c) 2014-2016 Akce
"""
import logging

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
