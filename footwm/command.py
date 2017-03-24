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

class Base:

    def __init__(self, display, windowid):
        super().__init__(display, windowid)
        # FootWM will monitor changes to this atom for actionable
        # commands.
        self.display.add_atom('FOOT_COMMANDV')

class ClientRootMixin(Base):
    """ Client interface for communicating with the Foot window manager. """

    def _setfootcommand(self, command):
        """ FOOT_COMMANDV """
        self.display.settextproperty(self, command, 'FOOT_COMMANDV')

    footcommand = property(fset=_setfootcommand, doc="FOOT_COMMANDV")

    def adddesktop(self, name, index):
        self.footcommand = ['desktop', 'insert', name, str(index)]

    def deletedesktop(self, index):
        self.footcommand = ['desktop', 'delete', str(index)]

    def renamedesktop(self, index, newname):
        self.footcommand = ['desktop', 'rename', str(index), newname]

class WmCommandReader:
    """ Window Manager Root window interface. """

    def __init__(self, display, root, desktop):
        self.display = display
        self.root = root
        self.desktop = desktop
        self.display.add_atom('FOOT_COMMANDV')

    @property
    def footcommand(self):
        """ FOOT_COMMANDV """
        return self.display.gettextproperty(self.root, 'FOOT_COMMANDV')

    def handle_propertynotify(self, atom):
        """ FOOT_COMMANDV propert change received, parse and action it. """
        if atom == self.display.atom['FOOT_COMMANDV']:
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

__all__ = ClientRootMixin, WmCommandReader
