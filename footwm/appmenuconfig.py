# Default configuration for appmenu.

TERMINAL = 'xterm'

# XXX should this be done all in python rather than calling the footmenu script?
DESKTOPMENU = TERMINAL + ' -e footmenu d'
WINDOWMENU = TERMINAL + ' -e footmenu w'

# Main/root menu.
menuconfig.addkey('a', label='Applications submenu', action=setmenu('apps'))
menuconfig.addkey('c', label='Start Console', action=run(TERMINAL))
menuconfig.addkey('d', label='Desktops', action=run(DESKTOPMENU))
menuconfig.addkey('f', label='Firefox', action=run('firefox'))
menuconfig.addkey('s', label='Search submenu', action=setmenu('search'))
menuconfig.addkey('w', label='Windows', action=run(WINDOWMENU))

## Apps menu.
menuconfig.addkey('f', label='Firefox', action=run('firefox'), keymapname='apps')

## Search menu.
searchcolumn = ('term', "Search term")
menuconfig.addkey('d', label='Duck Duck Go', action=runform('surfraw duckduckgo {term}', fields=[searchcolumn]), keymapname='search')
menuconfig.addkey('i', label='IMDB', action=runform('surfraw imdb {term}', fields=[searchcolumn]), keymapname='search')
menuconfig.addkey('s', label='Surfraw search', action=runform('surfraw {engine} {term}', fields=[('engine', 'Engine'), searchcolumn]), keymapname='search')
menuconfig.addkey('w', label='wikipedia', action=runform('surfraw wikipedia {term}', fields=[searchcolumn]), keymapname='search')
