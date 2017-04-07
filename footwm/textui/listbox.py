# Python standard modules.
import curses

# Local modules.
from . import common
from .. import log as logmodule
from . import util

log = logmodule.make(name=__name__)

class Model:
    """ The data that the listbox will display. """

    def __init__(self, showindex=True, showheader=True, rows=None, columns=None):
        # When inserting rows, the model always inserts two if its own housekeeping columns.
        # display index and a unique key id.
        self._indexcolumn = ListColumn(name='__index', label=' # ', visible=showindex)
        self._keycolumn = ListColumn(name='__key', label='KEY', visible=False)
        # Store the original columns and rows before any filtering.
        self.rows = rows
        self.columns = columns
        self._showheader = showheader
        self.selectedindex = 0
        self.views = []

    @property
    def showheader(self):
        # Can only show the column header if there are some visible columns.
        return self._showheader and self.visiblecolumns

    def attachview(self, view):
        self.views.append(view)

    def updateviews(self):
        for v in self.views:
            v.draw()

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, cols):
        self._columns = [self._indexcolumn, self._keycolumn] + (cols or [])

    @property
    def visiblecolumns(self):
        """ Columns to be displayed by views. """
        return [col for col in self.columns if col.visible]

    @property
    def rows(self):
        return self._rows

    @rows.setter
    def rows(self, r):
        indexname = self._indexcolumn.name
        keyname = self._keycolumn.name
        self._rows = [dict([[keyname, i], [indexname, "{:2d}".format(i + 1)]] + list(rowdict.items())) for i, rowdict in enumerate(r or [[]])]

    def _iscolumnvisible(self, name):
        visible = False
        for c in self._columns:
            if c.name == name:
                visible = c.visible
                break
        return visible

    @property
    def displayrows(self):
        """ Only include visible columns of the rows, each row value is converted to a list in column order. """
        visiblecolumns = self.visiblecolumns
        return [[row[column.name] for column in visiblecolumns] for row in self.rows]

    @property
    def selected(self):
        return self._rows[self.selectedindex]

#    @selected.setter
#    def selected(self, newindex):
#        try:
#            item = self.model.rows[newindex]
#        except IndexError:
#            log.error('ListBox.selected failed. index=%d out of range=%d!', newindex, len(self.model.rows))
#        else:
#            log.debug('newindex=%s oldindex=%s newlabel=%s', newindex, self.model.selectedindex, item)
#            self.model.selectedindex = newindex
#            self._update_viewport()

    def up(self):
        for v in self.views:
            v.up()

    def down(self):
        for v in self.views:
            v.down()

    def pageup(self):
        for v in self.views:
            v.pageup()

    def pagedown(self):
        for v in self.views:
            v.pagedown()

class ListColumn:
    """ Column display specification. """

    def __init__(self, name, visible=True, label=None):
        self.name = name
        self.visible = visible
        self.label = label

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
        headerlines = 2 if self.model.showheader else 0
        maxrows = geom.h - borders - headerlines
        # Get our slice of display items, then display them.
        sl = self.model.displayrows[self._viewport_index:self._viewport_index + maxrows]
        ## Calculate the max width of each column.
        columns = self.model.visiblecolumns if self.model.showheader else []
        maxwidths = self._calcmaxwidths(columns, sl)

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
        if self.model.showheader:
            ybase += 1
            xpos = xbase
            for rm, column in zip(maxwidths, columns):
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
        #log.debug('listbox.draw len(slice)=%s h=%s viewport_index=%s', len(sl), self.h, self._viewport_index)
        ybase += 1
        currentindex = self.model.selectedindex - self._viewport_index
        for i, row in enumerate(sl):
            if i == currentindex:
                textcolour = curses.color_pair(0) | curses.A_BOLD
            else:
                textcolour = curses.color_pair(0)
            xpos = xbase
            for rowmax, field in zip(maxwidths, row):
                text = util.clip_end(field, geom.w - 1)
                self._win.addstr(ybase, xpos, text, textcolour)
                xpos += rowmax + 3
            ybase += 1
        super().draw()

    def down(self):
        self._down(1)

    def pagedown(self):
        self._down(self._scroll)

    def _down(self, count):
        self.model.selectedindex += count
        if self.model.selectedindex >= len(self.model.rows):
            self.model.selectedindex = len(self.model.rows) - 1
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

    def _calcmaxwidths(self, columns, visiblerows):
        # Note that the column headers are included in this calculation!
        maxwidths = []
        for i, row in enumerate([columns] + visiblerows, 1):
            for j, col in enumerate(row):
                try:
                    length = len(col.label)
                except AttributeError:
                    length = len(col)
                try:
                    oldmax = maxwidths[j]
                except IndexError:
                    maxwidths.append(length)
                else:
                    maxwidths[j] = max(maxwidths[j], length)
        return maxwidths
