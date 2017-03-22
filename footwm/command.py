"""
Atom FOOT_COMMANDV parser and handler.

Unfortunately ICCCM/EWMH can't be used for some features
that I'd like for this WM. Eg, Dynamic desktops, windows
belonging to more than one desktop etc.

Custom foot commands will go through the FOOT_COMMANDV (foot command
vector) atom, so named because like argv (argument vector), it's a
list of strings.
"""

from . import log as logmodule

log = logmodule.make(name=__name__)

class BaseFootCommand:

    def __init__(self, display, root):
        self.display = display
        self.root = root
        # FootWM will monitor changes to this atom for actionable
        # commands.
        self.display.add_atom('FOOT_COMMANDV')

class FootCommandClient(BaseFootCommand):
    """ Client interface for communicating with the Foot window manager. """

    def _setfootcommand(self, command):
        """ FOOT_COMMANDV """
        self.display.settextproperty(self.root, command, 'FOOT_COMMANDV')

    footcommand = property(fset=_setfootcommand, doc="FOOT_COMMANDV")

    def adddesktop(self, name, index):
        self.footcommand = ['desktop', 'insert', name, str(index)]

    def deletedesktop(self, index):
        self.footcommand = ['desktop', 'delete', str(index)]

    def renamedesktop(self, index, newname):
        self.footcommand = ['desktop', 'rename', str(index), newname]

    def selectdesktop(self, index):
        self.footcommand = ['desktop', 'select', str(index)]

class FootCommandWM(BaseFootCommand):

    def __init__(self, display, root, desktop):
        super().__init__(display, root)
        self.desktop = desktop

    @property
    def footcommand(self):
        """ FOOT_COMMANDV """
        return self.display.gettextproperty(self.root, 'FOOT_COMMANDV')

    def action(self):
        """ FOOT_COMMANDV propert change received, parse and action it. """
        commandv = self.footcommand
        log.debug('command received: %s', str(commandv))
        command, subcommand = commandv[:2]
        if command == 'desktop':
            # Command modifies desktops in some way.
            if subcommand == 'insert':
                # Insert desktop
                name = commandv[2]
                index = int(commandv[3])
                self.desktop.adddesktop(name=name, index=index)
            elif subcommand == 'delete':
                # Delete desktop
                index = int(commandv[2])
                self.desktop.deletedesktop(index=index)
            elif subcommand == 'rename':
                # Rename desktop
                index = int(commandv[2])
                name = commandv[3]
                self.desktop.renamedesktop(index=index, newname=name)
            elif subcommand == 'select':
                # Select desktop
                index = int(commandv[2])
                self.desktop.selectdesktop(index=index)
        elif command == 'window':
            # Command modifies a window in some way.
            # Copy to desktop
            # Move to desktop
            # Make global/sticky
            # Remove from desktop
            # Remove from all desktops
            pass
        else:
            # Unknown command.
            pass
