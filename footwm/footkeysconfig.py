from .footrun import run

TERMINAL = 'xterm'

# Order windows using most recently used.
stacking = True

# Require scroll-lock for all our keys and always ignore caps-lock and numlock.
# This way, we can use the function keys for regular actions (if required by apps) by toggling off scroll-lock.
capslock = xlib.KeyModifierMask.Lock
alt = xlib.KeyModifierMask.Mod1
numlock = xlib.KeyModifierMask.Mod2
scrolllock = xlib.KeyModifierMask.Mod3
keyconfig.setmodifiers(requiremods=[scrolllock], ignoremods=[capslock, numlock])

# Window select.
keyconfig.addkey('F1', action=do(client.activatewindow, stacking=stacking, index=1))
keyconfig.addkey('F2', action=do(client.activatewindow, stacking=stacking, index=2))
keyconfig.addkey('F3', action=do(client.activatewindow, stacking=stacking, index=3))
keyconfig.addkey('F4', action=do(client.closewindow, stacking=stacking, index=0))

# Group select.
keyconfig.addkey('F5', action=do(client.selectdesktop, index=1))
keyconfig.addkey('F6', action=do(client.selectdesktop, index=2))
keyconfig.addkey('F7', action=do(client.selectdesktop, index=3))
keyconfig.addkey('F8', action=do(client.deletedesktop, index=0))

# Menus.
# Window select menu.
keyconfig.addkey('F9', action=do(run, TERMINAL + ' -e footmenu w'))
# Desktop select menu.
keyconfig.addkey('F10', action=do(run, TERMINAL + ' -e footmenu d'))

# ALT + ENTER : Runs an xterm. Requires a running footrun daemon.
keyconfig.addkey('Return', requiremods=[alt], action=do(run, TERMINAL))
