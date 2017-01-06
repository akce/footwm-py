import functools

# Order windows using most recently used.
stacking = True

# Require scroll-lock for all our keys and always ignore caps-lock and numlock.
# This way, we can use the function keys for regular actions (if required by apps) by toggling off scroll-lock.
capslock = xlib.KeyModifierMask.Lock
numlock = xlib.KeyModifierMask.Mod2
scrolllock = xlib.KeyModifierMask.Mod3
keyconfig.setmodifiers(requiremods=[scrolllock], ignoremods=[capslock, numlock])

# Window select.
keyconfig.addkey('F5', functools.partial(client.activatewindow, stacking=stacking, index=1))
keyconfig.addkey('F6', functools.partial(client.activatewindow, stacking=stacking, index=2))
keyconfig.addkey('F7', functools.partial(client.activatewindow, stacking=stacking, index=3))
keyconfig.addkey('F8', functools.partial(client.activatewindow, stacking=stacking, index=4))
