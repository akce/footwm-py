
# Python standard modules.
import argparse
import collections
import functools

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
        self.eventmap = collections.ChainMap()
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
        self.eventmap.maps.append(self.navkeys)

    def stop(self):
        self.scr.running = False

    def close(self):
        self.scr.close()

    def setmenu(self, keymapname):
        if keymapname in self.menu:
            self.eventmap = collections.ChainMap(self.menu[keymapname], self.navkeys)
            self.currmenu = keymapname
            self._model.rows = self._makerows()
            self._model.view.updatedisplay()

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

    def _makerows(self):
        return [{'key': a.key, 'label': a.label, 'cmd': a.action} for code, a in self.menu[self.currmenu].items()]

    def _makemodel(self):
        columns = [listbox.ListColumn(name='key', label='Key'),
                   listbox.ListColumn(name='label', label='Label'),
                   listbox.ListColumn(name='cmd', label='Command line', visible=False),
            ]
        model = listbox.Model(rows=self._makerows(), columns=columns)
        return model

    def config(self):
        return keyconfig.KeyBuilder(installer=self._installmenu)

    def _installmenu(self, menu):
        self.menu = menu
        self.eventmap.maps.append(menu[self.currmenu])

    def activateselection(self):
        row = self._model.selected
        command = row['cmd']
        try:
            command()
        finally:
            pass

    def editend(self, model, run, command):
        data = dict([(k, v) for k, v in zip([c.name for c in model.columns if c.visible], model.displayrows[0].cells(model.columns, visibleonly=True))])
        # HACK: Assumes that run is a DoAfter object, so we have to:
        # -> run(command) :: DoAfter.__call__(command) -> doafterfunc
        # -> doafterfunc()
        # I would rather if this was not tied to DoAfter()...
        run(command.format(**data))()

    def readform(self, command, fields, run):
        """ Opens a read form dialog, applying the results to the current row cmd. """
        ## Note that we're using a new listbox in edit-row-mode for our form reader.
        columns = [listbox.ListColumn(name=n, label=l) for n, l in fields]
        model = listbox.Model(rows=[dict([(c.name, '') for c in columns])], columns=columns)
        model.view = listbox.ListBox(model=model, parent=self._model.view)
        model.view.top()
        # Edit the first field.
        self.scr.windows.append(model.view)
        # Set the input keymap.
        endfunc = functools.partial(self.editend, command=command, run=run)
        model.editstart(rownum=0, columnname=fields[0][0], validator=self.editvalidator, endfunc=endfunc, cancelfunc=self.stop)
        self.eventmap = model.editeventmap
        # TODO Display a context/completion window.
        self.scr.draw()
        self.scr.run()

    def editvalidator(self, oldvalue, newvalue):
        return True

class DoAfter:
    """ A double-callable functools.partial that also calls 'after' after the func has been run. """

    def __init__(self, func, after=None, **kwargs):
        # Set the after attribute to be some sort of zero-arg callable.
        self.after = after
        self.func = func
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        def doafterfunc():
            self.func(*args, **dict([(k, v) for k, v in self.kwargs.items()] + [(k, v) for k, v in kwargs.items()]))
            if callable(self.after):
                self.after()
        return doafterfunc

def appmenu(args):
    """ Application menu. Applications can be any valid python code. """
    appmenu = AppMenu(msgduration=args.msgduration)
    with appmenu.config() as menuconfig:
        # Create some config objects and add them into the configs
        # namespace. eg, things that would be handy and used by most configs.
        gl = globals().copy()
        gl['akce'] = DoAfter(after=appmenu.stop, func=footrun.run, address=None)
        gl['run'] = gl['akce']
        gl['appmenu'] = appmenu
        gl['runform'] = DoAfter(func=appmenu.readform, run=gl['akce'])
        gl['setmenu'] = DoAfter(func=appmenu.setmenu)
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
