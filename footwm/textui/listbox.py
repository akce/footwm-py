# Python standard modules.
import curses
import itertools

# Local modules.
from . import common
from .. import log as logmodule
from . import util

log = logmodule.make(name=__name__)

class Model:
    """ The data that the listbox will display. """

    def __init__(self, showindex=True, showheader=True, rows=None, columns=None):
        # The model always inserts its own housekeeping columns.
        # unique key id.
        self._uidcolumn = ListColumn(name='_uid', label='UID', visible=False)
        # Store the original columns and rows before any filtering.
        self.rows = rows
        self.columns = columns
        self.showheader = showheader
        self.selectedindex = 0
        self.view = None

    @property
    def drawheader(self):
        return self.showheader and any(col.label for col in self.columns if col.visible)

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, cols):
        self._columns = [self._uidcolumn] + (cols or [])

    @property
    def rows(self):
        return self._rows

    @rows.setter
    def rows(self, rowdictlist):
        """ Note that rows are converted to an internal row representation. """
        uidname = self._uidcolumn.name
        self._rows = [ListRowStatic([[uidname, uid]] + list(rowdict.items())) for uid, rowdict in enumerate(rowdictlist)]

    @property
    def selected(self):
        return self.rows[self.selectedindex].data

    def up(self):
        self.view.up()

    def down(self):
        self.view.down()

    def pageup(self):
        self.view.pageup()

    def pagedown(self):
        self.view.pagedown()

    def calcmaxwidths(self, start, stop, includeheader=False):
        maxwidths = [len(col.label) if includeheader else 0 for col in self.columns if col.visible]
        for row in itertools.islice(self.rows, start, stop):
            for j, cell in enumerate(row.cells(self.columns, visibleonly=True)):
                maxwidths[j] = max(maxwidths[j], len(cell))
        return maxwidths

class ListColumn:
    """ Column display specification. """

    def __init__(self, name, visible=True, label=None):
        self.name = name
        self.visible = visible
        self.label = label or ""

def alwaystrue(x):
    return True

def isvisible(x):
    return x.visible

class ListRowStatic:

    def __init__(self, iterable):
        self.data = dict(iterable)

    def cells(self, columns, visibleonly=False):
        pred = isvisible if visibleonly else alwaystrue
        return [self.data[c.name] for c in columns if pred(c)]

class ListBox(common.PanelWindowMixin):

    def __init__(self, model, parent, geom=None):
        self.model = model
        self._viewport_index = 0
        super().__init__(parent, geom)
        self._update_scroll()

    def _update_scroll(self):
        # Ensure _scroll is at least 1, no point having a zero scroll value.
        self._scroll = max(int(self._geom.h / 2), 1)

    def resize(self, geom):
        super().resize(geom)
        self._update_scroll()
        self._update_viewport()

    def draw(self):
        ## Setup common colours.
        columncolour = curses.color_pair(0)
        headercolour = columncolour
        self._win.erase()
        self._win.box()
        geom = self._geom
        borders = 2
        headerlines = 2 if self.model.drawheader else 0
        maxrows = geom.h - borders - headerlines
        # Get our slice of display items, then display them.
        displayslice = slice(self._viewport_index, self._viewport_index + maxrows)
        ## Calculate the max width of each column.
        # Note that the column headers are included only when there's something to display, ie drawheader is True.
        maxwidths = self.model.calcmaxwidths(displayslice.start, displayslice.stop, includeheader=headerlines > 0)

        ## Draw the verticle column divider lines.
        xbase = 2
        ybase = 0
        xpos = xbase
        # Don't draw the last column.
        for rm in maxwidths[:-1]:
            xpos += rm + 1
            self._win.addch(ybase, xpos, curses.ACS_TTEE)
            self._win.vline(ybase + 1, xpos, curses.ACS_VLINE, geom.h - ybase - 1)
            self._win.addch(geom.h - 1, xpos, curses.ACS_BTEE)
            xpos += 2

        ## Draw column headers.
        if headerlines > 0:
            ybase += 1
            xpos = xbase
            visiblecolumns = [col for col in self.model.columns if col.visible]
            for rm, column in zip(maxwidths, visiblecolumns):
                self._win.addstr(ybase, xpos, column.label, headercolour)
                xpos += rm + 3
            ## Draw column header divider line.
            ybase += 1
            self._win.addch(ybase, geom.x, curses.ACS_LTEE)
            xpos = 1
            self._win.hline(ybase, xpos, curses.ACS_HLINE, geom.w - borders)
            xpos = xbase
            for rm in maxwidths[:-1]:
                xpos += rm + 1
                self._win.addch(ybase, xpos, curses.ACS_PLUS)
                xpos += 2
            self._win.addch(ybase, geom.w - 1, curses.ACS_RTEE)

        ## Draw row contents.
        ybase += 1
        currentindex = self.model.selectedindex - self._viewport_index
        for i, row in enumerate(self.model.rows[displayslice]):
            if i == currentindex:
                textcolour = curses.color_pair(0) | curses.A_BOLD
            else:
                textcolour = curses.color_pair(0)
            xpos = xbase
            for rowmax, cell in zip(maxwidths, row.cells(self.model.columns, visibleonly=True)):
                text = util.clip_end(cell, geom.w - 1)
                self._win.addstr(ybase, xpos, text, textcolour)
                xpos += rowmax + 3
            ybase += 1
        super().draw()

    def down(self):
        self._down(1)

    def pagedown(self):
        self._down(self._scroll)

    def _down(self, count):
        self.model.selectedindex = min(self.model.selectedindex + count, len(self.model.displayrows) - 1)
        self._update_viewport()

    def up(self):
        self._up(1)

    def pageup(self):
        self._up(self._scroll)

    def _up(self, count):
        self.model.selectedindex = max(self.model.selectedindex - count, 0)
        self._update_viewport()

    def _update_viewport(self):
        """ Calculates _viewport_index position w/respect to screen LINES. Scroll the viewport if needed. """
        # Is the selected item visible on screen?
        geom = self._geom
        log.debug('update_viewport old listbox=%s _selected_index=%s _viewport_index=%s _scroll=%s', geom, self.model.selectedindex, self._viewport_index, self._scroll)
        # offset makes sure that the selected item is visible on screen.
        # This calc only works because self._scroll is h/2. Doing the subtraction accounts for case where self.h == 1.
        # Could probably do this nicer but it works for now..
        offset = geom.h - self._scroll
        if self.model.selectedindex < self._viewport_index:
            # Selected item is above viewport, try and centre the item on screen.
            self._viewport_index = max(self.model.selectedindex - offset, 0)
        elif self.model.selectedindex >= (self._viewport_index + geom.h):
            # Selected item is below viewport+pageheight, try and centre the item on screen.
            self._viewport_index = self.model.selectedindex - offset
        log.debug('update_viewport new listbox=%s _selected_index=%s _viewport_index=%s _scroll=%s', geom, self.model.selectedindex, self._viewport_index, self._scroll)
