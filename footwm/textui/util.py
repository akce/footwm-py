
# Local modules.
from .. import log as logmodule

log = logmodule.make(name=__name__)


def thread_safe(func):
    """ Make access to the decorated function thread safe. """
    def wrapper(self, *args, **kwargs):
        with self.lock:
            ret = func(self, *args, **kwargs)
        return ret
    return wrapper

def time_to_display(hrs, mins, secs):
    if hrs == 0:
        ret = '{:02d}:{:02d}'.format(mins, secs)
    else:
        ret = '{:02d}:{:02d}:{:02d}'.format(hrs, mins, secs)
    return ret

def seconds_to_hours(total):
    """ Convert integer seconds to display string HH:MM:SS """
    mins = int(total / 60)
    secs = total % 60
    hrs = int(mins / 60)
    return hrs, mins % 60, secs

def clip_start(path, maxwidth, prefix='...'):
    if len(path) > maxwidth:
        newpath = prefix + path[(len(path) - maxwidth) + len(prefix):]
    else:
        newpath = path
    return newpath

def clip_end(label, width, suffix='...'):
    """ Returns a clipped version of the label string in order to fit within the display area. """
    if len(label) > width:
        newlabel = label[:width - len(suffix)] + suffix
    else:
        newlabel = label
    return newlabel
