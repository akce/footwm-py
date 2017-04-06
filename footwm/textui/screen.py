# Python standard modules.
import curses
from curses import panel
import threading

# Local modules.
from .. import log as logmodule
from . import common

log = logmodule.make(name=__name__)

class Screen(object):
    """ Application screen.
    Manages display of individual widgets on screen. """

    def __init__(self, app):
        self.app = app
        self._running = threading.Event()

    def init(self):
        ## ** Taken from curses.wrapper()
        # Initialise curses
        self.stdscr = curses.initscr()

        # Turn off echoing of keys, and enter cbreak mode,
        # where no buffering is performed on keyboard input
        curses.noecho()
        curses.cbreak()

        # In keypad mode, escape sequences for special keys
        # (like the cursor keys) will be interpreted and
        # a special value like curses.KEY_LEFT will be returned
        self.stdscr.keypad(1)

        # Start color, too.  Harmless if the terminal doesn't have
        # color; user can test with has_color() later on.  The try/catch
        # works around a minor bit of over-conscientiousness in the curses
        # module -- the error return from C start_color() is ignorable.
        try:
            curses.start_color()
        except:
            pass

        # Hide the cursor, text input is turned off.
        curses.curs_set(False)

        # Setup colours.
        curses.use_default_colors()     # Allow transparent colour.
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_GREEN)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        # Guru meditation!
        curses.init_pair(4, curses.COLOR_RED, -1)

    def close(self):
        ## ** Taken from curses.wrapper()
        self.stdscr.keypad(0)
        curses.echo()
        curses.nocbreak()
        curses.endwin()

    def subwin(self, h, w, y, x):
        return self.stdscr.subwin(h, w, y, x)

    @property
    def geom(self):
        y, x = self.stdscr.getbegyx()
        h, w = self.stdscr.getmaxyx()
        return common.Geometry(x=x, y=y, w=w, h=h)

    @property
    def running(self):
        return self._running.is_set()

    @running.setter
    def running(self, value):
        if value is True:
            self._running.set()
        else:
            self._running.clear()

    def run(self):
        try:
            self.init()
            self.running = True
            while self.running:
                self.handle_input()
        finally:
            self.close()

    def handle_input(self):
        k = self.stdscr.getch()
        self.app.on_user_event(k)

    def draw(self):
        """ Draws all our windows to virtual and then syncs the physical screen to the virtual screen. """
        for win in self.windows:
            win.draw()
        curses.doupdate()
