# Python standard modules.
import curses

# Local modules.
from . import common
from .. import log as logmodule
from . import util

log = logmodule.make(name=__name__)

class Model:
    """ The data that the listbox will display. """

    def __init__(self, contents=None):
        self.contents = contents or []
        self.views = []

    def __getitem__(self, index):
        """ Return a list row. """
        return self.contents[index]

    def __setitem__(self, index, row):
        self.contents[index] = row

    def __len__(self):
        return len(self.contents)

class ListBox(common.PanelWindowMixin):

    def __init__(self, parent, geom=None):
        self._reset()
        super().__init__(parent, geom)
        self._update_scroll()

    def _update_scroll(self):
        # Ensure _scroll is at least 1, no point having a zero scroll value.
        self._scroll = max(int(self._geom.h / 2), 1)

    def _reset(self):
        self._viewport_index = 0
        self._selected_index = 0

    def resize(self, geom):
        super().resize(geom)
        self._update_scroll()
        self._update_viewport()

    def draw(self):
        # Check show/hide state first.
        self._win.erase()
        geom = self._geom
        # Get our slice of display items, then display them.
        sl = self.contents[self._viewport_index:self._viewport_index + geom.h]
        #log.debug('listbox.draw len(slice)=%s h=%s viewport_index=%s', len(sl), self.h, self._viewport_index)
        for i, label in enumerate(sl):
            if i == (self._selected_index - self._viewport_index):
                colour = curses.color_pair(0) | curses.A_REVERSE
            else:
                colour = curses.color_pair(0)
            self._win.addstr(i, 0, util.clip_end(label, geom.w), colour)
        super().draw()

    def down(self):
        self._down(1)

    def pagedown(self):
        self._down(self._scroll)

    def _down(self, count):
        self._selected_index += count
        if self._selected_index >= len(self.contents):
            self._selected_index = len(self.contents) - 1
        self._update_viewport()

    def up(self):
        self._up(1)

    def pageup(self):
        self._up(self._scroll)

    def _up(self, count):
        self._selected_index = max(self._selected_index - count, 0)
        self._update_viewport()

    def _update_viewport(self):
        """ Calculates _viewport_index position w/respect to screen LINES. Scroll the viewport if needed. """
        # Is the selected item visible on screen?
        geom = self._geom
        log.debug('update_viewport old listbox=%s _selected_index=%s _viewport_index=%s _scroll=%s', geom, self._selected_index, self._viewport_index, self._scroll)
        # offset makes sure that the selected item is visible on screen.
        # This calc only works because self._scroll is h/2. Doing the subtraction accounts for case where self.h == 1.
        # Could probably do this nicer but it works for now..
        offset = geom.h - self._scroll
        if self._selected_index < self._viewport_index:
            # Selected item is above viewport, try and centre the item on screen.
            self._viewport_index = max(self._selected_index - offset, 0)
        elif self._selected_index >= (self._viewport_index + geom.h):
            # Selected item is below viewport+pageheight, try and centre the item on screen.
            self._viewport_index = self._selected_index - offset
        log.debug('update_viewport new listbox=%s _selected_index=%s _viewport_index=%s _scroll=%s', geom, self._selected_index, self._viewport_index, self._scroll)

    @property
    def selected(self):
        """ Return the current selected index. """
        return self._selected_index

    @selected.setter
    def selected(self, newindex):
        try:
            item = self.contents[newindex]
        except IndexError:
            log.error('ListBox.selected failed. index=%d out of range=%d!', newindex, len(self.contents))
        else:
            log.debug('newindex=%s oldindex=%s newlabel=%s', newindex, self._selected_index, item)
            self._selected_index = newindex
            self._update_viewport()

    @property
    def contents(self):
        return self._contents

    @contents.setter
    def contents(self, value):
        self._reset()
        self._contents = value
