"""
Simple xevent generator.

Copyright (c) 2016 Jerry Kotland
"""

from . import log as logger
from . import xlib

log = logger.make(name=__name__)

def run(display, eventhandlers):
    while True:
        try:
            xevent(display, eventhandlers)
        except Exception as e:
            log.exception(e)

def xevent(display, eventhandlers):
    event = display.nextevent
    e = xlib.EventName(event.type)
    #log.debug('event: %s', e)
    try:
        handler = eventhandlers[e.value]
    except KeyError:
        log.error('unhandled event %s', e)
    else:
        handler(event)
