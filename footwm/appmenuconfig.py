# Default configuration for appmenu.

# XXX should this be done all in python rather than calling the footmenu script?
DESKTOPMENU = 'footmenu d'
WINDOWMENU = 'footmenu w'

TERMINAL = 'xterm'

# Main/root menu.
menuconfig.addkey('c', label='Start Console', action=run(TERMINAL))
menuconfig.addkey('f', label='Firefox', action=run('firefox'))

# Submenus.
#menuconfig.addkey('a', label='Applications submenu', action=menu.setkeymap('apps'))
#menuconfig.addkey('d', label='Desktops', action=run(DESKTOPMENU))
#menuconfig.addkey('s', label='Search submenu', action=menu.setkeymap('search'))
#menuconfig.addkey('w', label='Windows', action=run(WINDOWMENU))

## Apps menu.
#menuconfig.addkey('f', label='Firefox', action=run('firefox'), keymapname='apps')

## Search menu.
# XXX how to add readline data into the command line?
# XXX eg, as a python format spec? "{line1} {line2}".format(line1, line2)?
# XXX readline as a function of menuconfig.
#menuconfig.addkey('d', label='Duck Duck Go', action=run('search --engine duckduckgo'), readline=True, readhistory='.history', keymapname='search')
# XXX readline as a function of the action itself.
#menuconfig.addkey('d', label='Duck Duck Go', action=run('search --engine duckduckgo', readline=True, readhistory='.history'), keymapname='search')

#menuconfig.addkey('i', label='IMDB', action=run('search --engine imdb'), keymapname='search')
#menuconfig.addkey('w', label='wikipedia', action=run('search --engine wikipedia'), keymapname='search')
