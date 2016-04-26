"""
Default logging setup.

Copyright (c) 2014-2016 Akce
"""
import logging

def make(name='foot', level=logging.DEBUG, formatter=None, handler=None):
    """ Logging init. Default configuration is for extended traceback information (useful for server) logging. """
    finstance = formatter or logging.Formatter('%(asctime)s %(name)s %(message)s')
    log = logging.getLogger(name)
    log.setLevel(level)
    if handler is None:
        h = logging.StreamHandler()
        #h = logging.NullHandler()
    else:
        h = handler
    h.setLevel(level)
    h.setFormatter(finstance)
    log.addHandler(h)
    return log
