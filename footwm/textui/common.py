
# Python standard modules.
import curses
from curses import panel

class Geometry:
    """ Entire screen if geom is None. """

    def __init__(self, x=None, y=None, w=None, h=None):
        # Default to max values if not supplied.
        self.x = x or 0
        self.y = y or 0
        self.w = w or curses.COLS
        self.h = h or curses.LINES

    def __str__(self):
        return 'Geometry(x={}, y={}, w={}, h={})'.format(self.x, self.y, self.w, self.h)

class WindowMixin:

    def __init__(self, parent, geom=None):
        self.parent = parent
        self._win = None
        if geom is None:
            y, x = parent.getbegyx()
            h, w = parent.getmaxyx()
            self.resize(Geometry(x=x, y=y, w=w, h=h))
        else:
            self.resize(geom)

    def resize(self, geom):
        self._geom = geom
        del self._win
        self._win = self.parent.subwin(self._geom.h, self._geom.w, self._geom.y, self._geom.x)

    def draw(self):
        """ Redraw window to virtual buffer. """
        self._win.noutrefresh()

    @property
    def x(self):
        return self._geom.x

    @property
    def y(self):
        return self._geom.y

    @property
    def h(self):
        return self._geom.h

    @property
    def w(self):
        return self._geom.w

class PanelWindowMixin:

    def __init__(self, parent, geom=None):
        super().__init__(parent, geom)
        self._panel = panel.new_panel(self._win)

    def resize(self, geom):
        super().resize(geom)
        self._panel.replace(self._win)

    def draw(self):
        super().draw()
        # Note update_panels updates all panels, so this should
        # ideally be in a staticmethod or into Screen.draw(). For now, assuming
        # that the library version checks its own dirty flag.
        curses.panel.update_panels()
