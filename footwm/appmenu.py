
# Python standard modules.
import argparse

# Local modules.
from . import clientcmd
from . import config
from . import footrun
from .textui import keyconfig
from .textui import listbox
from .textui import msgwin
from .textui import screen
from .textui import util

def xinit(displayname=None):
    display, root = clientcmd.makedisplayroot(displayname)
    client = clientcmd.ClientCommand(root)
    return client, display, root

class AppMixin:

    def __init__(self, msgduration=1.2):
        self._msgduration = msgduration
        self.scr = screen.Screen(self)

    def run(self):
        self._model = self._makemodel()
        ## XXX Putting this here breaks the inheritance logic.... Need to find a better structure....
        with keyconfig.KeyBuilder(installer=self._installnavkeys) as kc:
            kc.addkey('q', self.stop)
            kc.addkey('ESC', self.stop)
            kc.addkey('ENTER', self.activateselection)
            kc.addkey('UP', self._model.up)
            kc.addkey('k', self._model.up)
            kc.addkey('DOWN', self._model.down)
            kc.addkey('j', self._model.down)
            kc.addkey('PAGEUP', self._model.pageup)
        self.scr.init()
        self._model.view = listbox.ListBox(model=self._model, parent=self.scr)
        self.scr.windows = [self._model.view]
        self.scr.draw()
        self.scr.run()

    def _installnavkeys(self, keymap):
        self.navkeys = keymap['root']

    def stop(self):
        self.scr.running = False

    def close(self):
        self.scr.close()

    @property
    def eventmap(self):
        # Merge the listbox nav keys and menu map.
        # Note the order, menu overrides navkeys.
        return dict([(k, v) for k, v in self.navkeys.items()] + [(k, v) for k, v in self.menu[self.currmenu].items()])

    def on_user_event(self, kid):
        try:
            func = self.eventmap[kid]
        except KeyError:
            pass
        else:
            func()
            self.scr.draw()

class AppMenu(AppMixin):

    def __init__(self, msgduration=1.2):
        super().__init__(msgduration)
        self.currmenu = 'root'

    def _makemodel(self):
        columns = [listbox.ListColumn(name='key', label='Key'),
                   listbox.ListColumn(name='label', label='Label'),
                   listbox.ListColumn(name='cmd', label='Command line', visible=False),
            ]
        model = listbox.Model(rows=[{'key': a.key, 'label': a.label, 'cmd': a.action} for code, a in self.menu[self.currmenu].items()], columns=columns)
        return model

    def config(self):
        return keyconfig.KeyBuilder(installer=self._installmenu)

    def _installmenu(self, menu):
        self.menu = menu

    def activateselection(self):
        row = self._model.selected
        command = row['cmd']
        try:
            command()
        finally:
            self.stop()

class LazyClient(clientcmd.ClientCommand):
    """ Connects to the X Server only on use. """

    def __init__(self, displayname, menu):
        self.displayname = displayname
        self.menu = menu

    def do(self, *args, **kwargs):
        self.cmd = args[0]
        self.args = args[1:]
        self.kwargs = kwargs
        return self

    def __call__(self):
        display, root = clientcmd.makedisplayroot(self.displayname)
        super().__init__(root)
        return self.cmd(*self.args, **self.kwargs)

class LazyRun:
    """ Connect to the footrun daemon only on use. """

    def __init__(self, menu, address=None):
        self.menu = menu
        self.address = address

    def __call__(self, *args, **kwargs):
        def stopafterrun():
            footrun.run(*args, address=self.address, **kwargs)
            self.menu.stop()
        return stopafterrun

def appmenu(args):
    """ Application menu. Applications can be any valid python code. """
    appmenu = AppMenu(msgduration=args.msgduration)
    with appmenu.config() as menuconfig:
        # Create a client object and add it into the configs
        # namespace. One of these is handy and would be used by every
        # config.
        gl = globals().copy()
        gl['x'] = LazyClient(args.displayname, appmenu)
        gl['akce'] = LazyRun(menu=appmenu)
        gl['run'] = gl['akce']
        gl['appmenu'] = appmenu
        config.loadconfig(args.config, gl, locals())
    try:
        appmenu.run()
    finally:
        appmenu.close()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--displayname', help='X display name.')
    parser.add_argument('--msgduration', default=1.2, type=float, help='Seconds to show message window before actioning')
    parser.add_argument('--escapedelay', default=25, type=int, help='Set curses escape delay')
    parser.add_argument('--config', default=config.getconfigwithfallback('appmenuconfig.py'), help='Configuration file. Default: %(default)s')
    return parser.parse_args()

def main():
    args = parse_args()
    util.setescapedelay(args.escapedelay)
    appmenu(args)
