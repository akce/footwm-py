
# Python standard modules.
import curses
from curses import panel

class Geometry:
    """ Entire screen if geom is None. """

    def __init__(self, x=None, y=None, w=None, h=None):
        # Default to max values if not supplied.
        self._x = x or 0
        self._y = y or 0
        self._w = w or curses.COLS
        self._h = h or curses.LINES

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def h(self):
        return self._h

    @property
    def w(self):
        return self._w

    def __str__(self):
        return 'Geometry(x={}, y={}, w={}, h={})'.format(self._x, self._y, self._w, self._h)

class WindowMixin:

    def __init__(self, parent, geom=None):
        self.parent = parent
        self._win = None
        if geom is None:
            self.resize(parent.geom)
        else:
            self.resize(geom)

    @property
    def geom(self):
        return self._geom

    def resize(self, geom):
        self._geom = geom
        del self._win
        self._win = self.parent.subwin(self._geom.h, self._geom.w, self._geom.y, self._geom.x)

    def draw(self):
        """ Redraw window to virtual buffer. """
        self._win.noutrefresh()

    def subwin(self, h, w, y, x):
        return self._win.subwin(h, w, y, x)

class PanelWindowMixin(WindowMixin):

    def __init__(self, parent, geom=None):
        super().__init__(parent, geom)
        # Note that self._panel will be created in resize().
        # That's because WindowMixin calls resize as part of __init__.

    def resize(self, geom):
        super().resize(geom)
        try:
            self._panel.replace(self._win)
        except AttributeError:
            self._panel = panel.new_panel(self._win)

    def top(self):
        self._panel.top()

    def draw(self):
        super().draw()
        # Note update_panels updates all panels, so this should
        # ideally be in a staticmethod or into Screen.draw(). For now, assuming
        # that the library version checks its own dirty flag.
        curses.panel.update_panels()
