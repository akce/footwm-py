"""
FootKeys module.

Copyright (c) 2016 Akce
"""
# Python standard modules.
import functools
import itertools
import operator
import os

# Local modules.
from . import clientcmd
from . import log as logger
from . import kb
from . import xevent
from . import xlib

log = logger.make(name=__name__)

__all__ = 'FootKeys',

def icsfactorial(modlist):
    """
    itertools.combinations factorial.

    >>> icsfactorial([1, 2])
    [(1,), (2,), (1, 2)]
    """
    def combos():
        for i in range(1, len(modlist) + 1):
            yield list(itertools.combinations(modlist, i))
    # sum flattens the list of combinations lists.
    return sum(combos(), [])

def iter2mask(iterable):
    """
    Convert an iterable to a mask.
    """
    return functools.reduce(operator.or_, iterable, 0)

class KeyAction:

    def __init__(self, key, action, requiremods=None, ignoremods=None):
        self.key = key
        self.action = action
        self.requiremods = requiremods or []
        self.ignoremods = ignoremods or []

    def __call__(self, *args, **kwargs):
        return self.action(*args, **kwargs)

class KeyBuilder:

    def __init__(self, footkeys):
        self.footkeys = footkeys
        # [KeyAction]
        self._keysymactions = []
        self._requiremods = None
        self._ignoremods = None

    def setmodifiers(self, requiremods=None, ignoremods=None):
        """ Sets global requiremods/ignoremods. """
        self._requiremods = requiremods
        self._ignoremods = ignoremods

    def addkey(self, keysym, action, requiremods=None, ignoremods=None):
        """ Adds a key/action pair to the keymap.
        requiremods & ignoremods are in addition to the global requiremods/ignoremods values.
        """
        # Don't apply the global modifiers, store them separately so we know what came from where.
        self._keysymactions.append(KeyAction(keysym, action=action, requiremods=requiremods, ignoremods=ignoremods))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # No exception occurred, install the keymap.
            self.footkeys._install(self._keysymactions, requiremods=self._requiremods, ignoremods=self._ignoremods)

class FootKeys(clientcmd.ClientInitMixin):

    def __init__(self, displayname=None):
        """
        FootKeys._handle_keypress() will apply requiremods & ignoremods to all grabbed keypresses.
        requiremods and ignoremods must be a set of footwm.xlib.KeyModifierMask values.
        All requiremods values must all be applied for a key in this keymap to match.
        All ignoremods values are all masked out and ignored in keypress events.
        """
        super().__init__(displayname=displayname)
        self._makehandlers()

    def _makehandlers(self):
        self.eventhandlers = {
                xlib.EventName.KeyPress:            self._handle_keypress,
                xlib.EventName.MappingNotify:       self._handle_mappingnotify,
                }

    def config(self):
        # Creating the KeyBuilder as a separate object so that the only way to
        # add keys is via a context manager. The context manager then forces
        # the call to _install the keys in the Xserver after all addkey calls
        # have been made.
        return KeyBuilder(self)

    def _install(self, keysymactions=None, requiremods=None, ignoremods=None):
        self._keysymactions = keysymactions
        self._requiremods = requiremods
        self._ignoremods = ignoremods
        self._rebuild()

    def _rebuild(self):
        # Reset the keycode action settings, and ungrab from Xserver.
        self.display.ungrabkey(xlib.AnyKey, xlib.GrabKeyModifierMask.AnyModifier, self.root)
        self._keycodeactions = []
        # Recreate keyboard settings, this loads the keysym to keycode bindings.
        self.keyboard = kb.Keyboard(self.display)
        # Convert the keysym action objects to xserver keycodes as the xkeyboard events are given to us as keycodes.
        self._keycodeactions = self._makekeycodes()
        self._installkeycodes()

    def _makekeycodes(self):
        keycodes = {}
        for ksa in self._keysymactions:
            # keymodifier would be a ShiftLock for capital letters, or NumLock for KP_*.
            # This keymodifier is always required for keycode.
            keycode, keymodifier = self.keyboard.keycodes[ksa.key]
            # requiremods are modifiers that are required for a key to match.
            requiremods = frozenset(([keymodifier] if keymodifier else []) + ksa.requiremods + self._requiremods)
            # ignoremods are the modifiers whose state we don't care about.
            # X requires us to explicitly register on/off states for each ignored key, hence the use of icsfactorial
            # to generate the requried combinations.
            # Note that requiremods are always removed from ignoremods.
            ignoremods = frozenset(ksa.ignoremods + self._ignoremods) - requiremods
            for mods in [()] + icsfactorial(ignoremods):
                kc = KeyAction(keycode, ksa, requiremods=requiremods.union(frozenset(mods)))
                keycodes[(keycode, iter2mask(kc.requiremods))] = kc
        return keycodes

    def _installkeycodes(self):
        """ Installs the key code actions with the x server. """
        self.root.manage(xlib.InputEventMask.KeyPress)
        for (keycode, keymodmask), keyaction in self._keycodeactions.items():
            log.debug('0x%08x: install keygrab keycode=0x%x modifier=0x%x', self.root.window, keycode, keymodmask)
            self.display.grabkey(keycode, keymodmask, self.root, True, xlib.GrabMode.Async, xlib.GrabMode.Async)

    def _handle_keypress(self, event):
        """ User has pressed a key that we've grabbed. """
        e = event.xkey
        log.debug('0x%08x: handle_keypress keycode=0x%x modifiers=%s', e.window, e.keycode, e.state.value)
        # Retrieve key action and call.
        keycombo = (e.keycode, e.state.value)
        if keycombo in self._keycodeactions:
            keyaction = self._keycodeactions[keycombo]
            keyaction.action.action()
        else:
            log.error('0x%08x: no action defined for (keycode, modifier) %s', e.window, keycombo)

    def _handle_mappingnotify(self, event):
        """ X server has had a keyboard mapping changed. Update our keyboard layer. """
        self._rebuild()

def nullop(*args, **kwargs):
    print('XXX')

def getconfigfilename(args):
    cf = None
    try:
        if args.configfile:
            cf = args.configfile
    except AttributeError:
        pass
    if cf is None:
        # Test if there's config file in the home directory.
        name = 'footkeysconfig.py'
        homefile = os.path.join(os.environ['HOME'], ".{}".format(name))
        if os.path.isfile(homefile):
            cf = homefile
        else:
            # Fallback to the sample config footkeysconfig.py in the source directory.
            cf = os.path.join(os.path.split(os.path.realpath(__file__))[0], name)
    return cf

def loadconfig(filename, globals_=None, locals_=None):
    gs = globals() if globals_ is None else globals_
    ls = locals() if locals_ is None else locals_
    with open(filename) as f:
        codeobj = compile(f.read(), filename, 'exec')
        exec(codeobj, gs, ls)

def parseargs():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--configfile', help='Full path to configuration file. default: %(default)s')
    parser.add_argument('--display', help='X display name. eg, :0.1. default: %(default)s')
    args = parser.parse_args()
    return args

def main():
    args = parseargs()
    fk = FootKeys(args.display)
    # TODO load settings from config file or use defaults.
    with fk.config() as keyconfig:
        # Create a client object and add it into the configs
        # namespace. One of these is handy and would be used by every
        # config.
        gl = globals().copy()
        gl['client'] = clientcmd.ClientCommand(fk.display, fk.root, fk.ewmh)
        loadconfig(getconfigfilename(args), gl, locals())
    try:
        xevent.run(fk.display, fk.eventhandlers)
    finally:
        fk.clearkeymap()
