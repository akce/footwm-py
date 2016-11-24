# Require scroll-lock for all our keys and always ignore caps-lock and numlock.
capslock = xlib.KeyModifierMask.Lock
numlock = xlib.KeyModifierMask.Mod2
scrolllock = xlib.KeyModifierMask.Mod3
fconfig.setmodifiers(requiremods=[scrolllock], ignoremods=[capslock, numlock])
fconfig.addkey('F5', nullop)
