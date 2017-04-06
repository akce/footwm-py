# Python standard modules.
import curses
import math
import threading

# Local modules.
from .. import log as logmodule
from . import common
from . import util

log = logmodule.make(name=__name__)

class Message(common.PanelWindowMixin):

    def __init__(self, lines, parent, geom=None, title='', countdown=None):
        self._title = title
        self._lines = lines
        if geom is None:
            _geom = self._make_geom(lines, parent)
        else:
            _geom = geom
        super().__init__(parent, _geom)
        self.countdown = countdown

    def _make_geom(self, lines, parent):
        """ Makes a centered geometry based on parent geometry and number of lines. """
        pg = parent.geom
        # Borders for both top/bottom, left/right, hence value of 2 instead of 1.
        self.borders = 2 * 1
        h = min(pg.h, len(lines) + self.borders)
        try:
            maxlinelens = max(*[len(j) for j in lines + [self._title]])
        except TypeError:
            # max(*[number]) will raise TypeError. Python * (apply operator) needs a len(list) > 1.
            maxlinelens = len(lines[0])
        w = min(pg.w, maxlinelens + self.borders)
        y = int(pg.h / 2) - int(h / 2)
        x = int(pg.w / 2) - int(w / 2)
        return common.Geometry(x=x, y=y, w=w, h=h)

    def _draw_countdown(self):
        # Split into a separate method so the countdown timer can update only
        # this portion of the screen and minimise flicker.
        if self.countdown is not None:
            cs = str(self.countdown)
            self._win.addstr(2, self._w - len(cs), cs)

    def draw(self):
        self._win.clear()
        self._win.attron(curses.color_pair(4) | curses.A_BOLD)
        self._win.box()
        self._win.attroff(curses.color_pair(4))
        self._win.addstr(0, 1, self._title)
        #self._draw_countdown()
        maxlinewidth = self.geom.w - self.borders
        for i, line in enumerate(self._lines, 1):
            self._win.addstr(i, 1, util.clip_end(line, maxlinewidth), 0)
        super().draw()
