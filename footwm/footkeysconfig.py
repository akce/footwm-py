from .footrun import run

TERMINAL = 'xterm -tn xterm-256color'

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
keyconfig.addkey('F4', action=do(client.activatewindow, stacking=stacking, index=4))

# Group select.
keyconfig.addkey('F5', action=do(client.selectdesktop, index=1))
keyconfig.addkey('F6', action=do(client.selectdesktop, index=2))
keyconfig.addkey('F7', action=do(client.selectdesktop, index=3))
keyconfig.addkey('F8', action=do(client.selectdesktop, index=4))

# Menus.
# Window select menu.
keyconfig.addkey('F9', action=do(run, TERMINAL + ' -e footmenu w'))
# Desktop select menu.
keyconfig.addkey('F10', action=do(run, TERMINAL + ' -e footmenu d'))

keyconfig.addkey('F11', action=do(client.closewindow, stacking=stacking, index=0))
keyconfig.addkey('F12', action=do(client.deletedesktop, index=0))

# App menu. I bind F20 to CAPSLOCK.
keyconfig.addkey('F20', action=do(run, TERMINAL + ' -e appmenu'))

# ALT + ENTER : Runs an xterm. Requires a running footrun daemon.
keyconfig.addkey('Return', requiremods=[alt], action=do(run, TERMINAL))
