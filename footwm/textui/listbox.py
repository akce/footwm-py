# Python standard modules.
import curses
from curses import ascii as cascii
import functools
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
        self.editeventmap = None

    def insertchar(self, char):
        self._editcell.insert(char)

    def backspace(self):
        self._editcell.backspace()

    def cursormove(self, delta):
        self._editcell.cursormove(delta)

    def delete(self):
        self._editcell.delete()

    def editnextcolumn(self):
        # Find the next column, and make that the only editcell.
        oldcolumnname = self._editcell.columnname
        cns = [c.name for c in self.columns if c.visible]
        offbyone = itertools.cycle(cns)
        next(offbyone)
        for c, n in zip(cns, offbyone):
            if c == oldcolumnname:
                nextcolumnname = n
                break
        else:
            # Internal error! Not found.
            raise Exception('Column name {} not found.'.format(oldcolumnname))
        # Make old editcell readonly.
        validator = self._editcell._validator
        self.editend()
        self._editcell = self._rows[0].edit(nextcolumnname, validator)

    def editstart(self, rownum, columnname, validator=None, endfunc=None, cancelfunc=None):
        # Build the edit keymap.
        if self.editeventmap is None:
            # Seed with printable character insertion.
            self.editeventmap = {kid: functools.partial(self.insertchar, chr(kid)) for kid in range(1, 255) if cascii.isprint(kid)}
            # Add control characters.
            self.editeventmap[curses.KEY_DC] = self.delete
            self.editeventmap[cascii.BS] = self.backspace
            self.editeventmap[cascii.DEL] = self.backspace
            self.editeventmap[curses.KEY_BACKSPACE] = self.backspace
            self.editeventmap[cascii.TAB] = self.editnextcolumn
            self.editeventmap[curses.KEY_LEFT] = functools.partial(self.cursormove, -1)
            self.editeventmap[curses.KEY_RIGHT] = functools.partial(self.cursormove, 1)
            self.editeventmap[cascii.NL] = functools.partial(self.editend, endfunc)
            if cancelfunc is not None:
                self.editeventmap[cascii.ESC] = cancelfunc
        self._editcell = self._rows[rownum].edit(columnname, validator)
        # Turn on the cursor in the view.
        # HACK! curses.curs_set(2) call doesn't work here for some reason. Resort to using the escape code directly.
        print("\033[?25h", end='', flush=True)

    def editend(self, endfunc=None):
        # Clear the editcell and return all rows back to readonly.
        oldcolumnname = self._editcell.columnname
        row = self._rows[0]
        row.data[oldcolumnname] = CellStatic(str(row.data[oldcolumnname]))
        self._editcell = None
        if endfunc is not None:
            endfunc(self)

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
        self._rows = [ListRow([[uidname, CellStatic(uid)]] + [[n, CellStatic(c)] for n, c in rowdict.items()]) for uid, rowdict in enumerate(rowdictlist)]

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

def alwaystrue(*args):
    return True

def isvisible(x):
    return x.visible

class ListRow:

    def __init__(self, iterable):
        self.data = dict(iterable)

    def cells(self, columns, visibleonly=False):
        pred = isvisible if visibleonly else alwaystrue
        try:
            return [self.data[c.name] for c in columns if pred(c)]
        except KeyError:
            raise Exception(str(list(self.data.items())))

    def edit(self, columnname, validator):
        cell = self.data[columnname]
        editcell = CellEdit(cell, columnname, validator=validator)
        self.data[columnname] = editcell
        return editcell

class CellStatic(str):

    def draw(self, window, x, y, maxw, textcolour):
        text = util.clip_end(self, maxw)
        # addstr seems to move the cursor, so put it back once we finish writing.
        cy, cx = window.getyx()
        window.addstr(y, x, text, textcolour)
        window.move(cy, cx)

class CellEdit:

    def __init__(self, contents, columnname, validator=None, cursorpos=0):
        self._str = contents
        self.columnname = columnname
        self.cursorpos = cursorpos
        self._validator = validator or alwaystrue

    def draw(self, window, x, y, maxw, textcolour):
        text = util.clip_end(self._str, maxw)
        window.addstr(y, x, text, textcolour)
        window.move(y, x + self.cursorpos)

    def insert(self, char):
        """ Insert char at cursorpos. """
        newstr = self._str[:self.cursorpos] + char + self._str[self.cursorpos:]
        if self._validator(self._str, newstr):
            self._str = newstr
            self.cursorpos += 1

    def backspace(self):
        """ Remove character to the left of cursorpos. """
        # We can't let cursorpos go negative, python array indexing has -1 == end of list which is not what we want!
        cp = max(self.cursorpos - 1, 0)
        newstr = self._str[:cp] + self._str[self.cursorpos:]
        if self._validator(self._str, newstr):
            self._str = newstr
            self.cursorpos = cp

    def cursormove(self, delta):
        if delta > 0:
            self.cursorpos = min(len(self._str), self.cursorpos + delta)
        elif delta < 0:
            self.cursorpos = max(0, self.cursorpos + delta)

    def delete(self):
        newstr = self._str[:self.cursorpos] + self._str[self.cursorpos + 1:]
        if self._validator(self._str, newstr):
            self._str = newstr

    def __len__(self):
        return len(self._str)

    def __str__(self):
        return self._str

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
                cell.draw(self._win, x=xpos, y=ybase, maxw=rowmax, textcolour=textcolour)
                xpos += rowmax + 3
            ybase += 1
        self._win.cursyncup()
        super().draw()

    def down(self):
        self._down(1)

    def pagedown(self):
        self._down(self._scroll)

    def _down(self, count):
        self.model.selectedindex = min(self.model.selectedindex + count, len(self.model.rows) - 1)
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
