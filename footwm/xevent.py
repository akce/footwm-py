"""
Simple xevent generator.

Copyright (c) 2016 Akce
"""
from . import log as logger
from . import xlib

def run(display, eventhandlers):
    # Setup a logger that is always running so that we can catch unhandled exceptions.
    # The logger will be module level elog object. Calling it elog so that it remains untouched by default invocations of
    # startlogging and stoplogging.
    logger.startlogging(modulenames=[__name__], levelname='error', outfilename='/tmp/footwmerrors.log', logobjname='elog')
    while True:
        try:
            xevent(display, eventhandlers)
        except Exception as e:
            elog.exception(e)

def xevent(display, eventhandlers):
    event = display.nextevent
    e = xlib.EventName(event.type)
    #log.debug('event: %s', e)
    try:
        handler = eventhandlers[e.value]
    except KeyError:
        elog.warn('unhandled event %s', e)
    else:
        handler(event)
