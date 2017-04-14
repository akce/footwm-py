import collections
import curses
from curses import ascii

keylabels = {
    ascii.NL:		'ENTER',
    ascii.ESC:		'ESC',
    ascii.DC4:		'SPACE',
    curses.KEY_NPAGE:	'PAGEDOWN',
    curses.KEY_PPAGE:	'PAGEUP',
    curses.KEY_UP:	'UP',
    curses.KEY_DOWN:	'DOWN',
    curses.KEY_LEFT:	'LEFT',
    curses.KEY_RIGHT:	'RIGHT',
    curses.KEY_HOME:	'HOME',
    curses.KEY_END:	'END',
    }

keycodes = {v: k for k, v in keylabels.items()}

class Key:

    def __init__(self, key, label, code, action):
        self.key = key
        self.label = label
        self.code = code
        self.action = action

    def __call__(self, *args, **kwargs):
        return self.action(*args, **kwargs)

class KeyBuilder:

    def __init__(self, installer):
        self._installer = installer
        self._keymaps = collections.defaultdict(collections.OrderedDict)

    def addkey(self, key, action, label='', keymapname='root'):
        """ Adds a key/action pair to the named keymap. """
        try:
            code = keycodes[key]
        except KeyError:
            code = ord(key)
        self._keymaps[keymapname][code] = Key(key=key, label=label, code=code, action=action)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # No exception occurred, install the keymap.
            self._installer(self._keymaps)
