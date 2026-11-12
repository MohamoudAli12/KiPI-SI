"""A bar under a box to drag it to the height wanted: one way to resize every list, table,
text box and section in the side panels.

:class:`HeightGrip` sets its box's height outright: dragged down the box grows, past the
dock's own height if need be (the panel round it grows and its scroll area scrolls);
dragged up it shrinks, down to the box's own minimum. A double-click puts back the
default height. :func:`add_grips` gives every list, table and text box of a panel one, and
keeps each height between starts.
"""

from __future__ import annotations

from typing import List, Optional

from qtpy.QtCore import QEvent, QObject, QPoint, QRect, QSettings, Qt, Signal
from qtpy.QtGui import QPainter, QPalette
from qtpy.QtWidgets import (QAbstractItemView, QBoxLayout, QComboBox, QFormLayout,
                            QHeaderView, QLayout, QPlainTextEdit, QSizePolicy, QStackedWidget,
                            QTabWidget, QTextEdit, QWidget)

_MIN = 40       # no box shrinks below this, whatever it says its minimum is


class HeightGrip(QWidget):
    height_changed = Signal(int)            # the box's new height, or 0: back to the default

    def __init__(self, view: QWidget, parent: Optional[QWidget] = None,
                 default: Optional[int] = None):
        super().__init__(parent)
        self.view = view
        view._height_grip = self
        # Never below what the box needs (a section's contents, a list's few rows).
        self.floor = max(view.minimumHeight(), view.minimumSizeHint().height(), _MIN)
        hint = min(view.sizeHint().height(), view.maximumHeight())
        self.default = max(int(default or hint), self.floor)
        self._press: Optional[QPoint] = None
        self._start = 0
        self.setFixedHeight(9)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.SizeVerCursor)
        self.setToolTip("Drag to make this taller or shorter (the panel scrolls); "
                        "double-click for its usual height")
        # Shown and hidden with its box (a list shown only once there are results).
        self.setHidden(view.isHidden())
        view.installEventFilter(self)
        self.set_height(self.default)

    def set_height(self, h: int):
        """The box's height: ``h`` (0: the default), never below its own minimum."""
        h = int(h) if h and int(h) > 0 else self.default
        h = max(h, self.floor)
        if (self.view.minimumHeight(), self.view.maximumHeight()) != (h, h):
            self.view.setFixedHeight(h)

    def eventFilter(self, obj, event):
        if obj is self.view and event.type() in (QEvent.ShowToParent, QEvent.HideToParent):
            self.setHidden(self.view.isHidden())
        return False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press = self._global(event)
            self._start = self.view.height()
        event.accept()

    def mouseMoveEvent(self, event):
        if self._press is not None:
            self.set_height(self._start + self._global(event).y() - self._press.y())
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._press is not None:
            self._press = None
            self.height_changed.emit(self.view.height())
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.set_height(0)
        self.height_changed.emit(0)
        event.accept()

    @staticmethod
    def _global(event) -> QPoint:
        p = event.globalPosition() if hasattr(event, "globalPosition") else event.globalPos()
        return p.toPoint() if hasattr(p, "toPoint") else p

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setPen(self.palette().color(QPalette.Mid))
        r: QRect = self.rect()
        cx, cy = r.center().x(), r.center().y()
        for dy in (-2, 0, 2):                           # three short lines: a handle
            p.drawLine(cx - 14, cy + dy, cx + 14, cy + dy)


def grip(view: QWidget, key: str, parent: Optional[QWidget] = None,
         default: Optional[int] = None) -> HeightGrip:
    """A grip for ``view`` whose height is kept between starts as ``view/<key>``; the
    caller lays it out under ``view``."""
    g = HeightGrip(view, parent if parent is not None else view.parentWidget(), default)
    settings = QSettings("KiPI-SI", "KiPI-SI")
    try:
        g.set_height(int(settings.value(f"view/{key}", 0) or 0))
    except (TypeError, ValueError):
        pass
    g.height_changed.connect(lambda h: settings.setValue(f"view/{key}", h))
    return g


def _layout_holding(widget: QWidget) -> Optional[QLayout]:
    """The layout ``widget`` is in: its parent's, or one nested in that."""
    parent = widget.parentWidget()
    todo = [parent.layout()] if parent is not None and parent.layout() is not None else []
    while todo:
        lay = todo.pop()
        if lay.indexOf(widget) >= 0:
            return lay
        for i in range(lay.count()):
            sub = lay.itemAt(i).layout()
            if sub is not None:
                todo.append(sub)
    return None


def _vertical(lay) -> bool:
    return isinstance(lay, QBoxLayout) and lay.direction() in (QBoxLayout.TopToBottom,
                                                               QBoxLayout.BottomToTop)


def _put_under(g: QWidget, widget: QWidget) -> bool:
    """Lay ``g`` out right under ``widget``; False when its layout has no room for it."""
    lay = _layout_holding(widget)
    if _vertical(lay):
        lay.insertWidget(lay.indexOf(widget) + 1, g)
        return True
    if isinstance(lay, QFormLayout):
        row, _role = lay.getWidgetPosition(widget)
        lay.insertRow(row + 1, g)
        return True
    if isinstance(lay, QBoxLayout):     # in a row: the grip goes under the row
        holder, outer = lay, lay.parent()
        while isinstance(outer, QLayout):
            if _vertical(outer):
                for i in range(outer.count()):
                    if outer.itemAt(i).layout() is holder:
                        outer.insertWidget(i + 1, g)
                        return True
            holder, outer = outer, outer.parent()
    return False


def pack_top(lay) -> None:
    """Every item of the column ``lay`` at the height it is given, the room to spare left
    at the bottom: a box stretched to fill the dock could not be dragged shorter."""
    if not _vertical(lay):
        return
    for i in range(lay.count()):
        lay.setStretch(i, 0)
    last = lay.itemAt(lay.count() - 1) if lay.count() else None
    if last is None or last.spacerItem() is None:
        lay.addStretch(1)
    else:
        lay.setStretch(lay.count() - 1, 1)


_VIEWS = (QAbstractItemView, QTextEdit, QPlainTextEdit)


def _targets(panel: QWidget) -> List[QWidget]:
    """The boxes of ``panel`` to give a grip: each list, table and text box (a tab page's
    own one through its tab widget), and each widget marked ``grip``."""
    out: List[QWidget] = []
    for w in panel.findChildren(QWidget):
        if isinstance(w, HeightGrip) or getattr(w, "_height_grip", None) is not None:
            continue
        if not (isinstance(w, _VIEWS) and not isinstance(w, QHeaderView)
                or w.property("grip") is True):
            continue
        a, skip = w.parentWidget(), False
        while a is not None and a is not panel:         # a combo box's own popup list
            if isinstance(a, QComboBox):
                skip = True
                break
            a = a.parentWidget()
        if skip:
            continue
        stack = w.parentWidget()
        if isinstance(stack, QStackedWidget) and isinstance(stack.parentWidget(), QTabWidget):
            w = stack.parentWidget()
            if getattr(w, "_height_grip", None) is not None:
                continue
        if w not in out:
            out.append(w)
    return out


class _TabFitter(QObject):
    """Holds a tab widget at the height of the page it shows. Qt sizes a tab widget by its
    tallest page, so a short page left blank space under it; the height follows a switch
    of page and any change in the shown page's height (a grip dragged in it)."""

    def __init__(self, tabs: QTabWidget):
        super().__init__(tabs)
        self.tabs = tabs
        for i in range(tabs.count()):
            tabs.widget(i).installEventFilter(self)
        tabs.currentChanged.connect(lambda _i: self.fit())
        self.fit()

    def fit(self):
        tabs = self.tabs
        page = tabs.currentWidget()
        if page is None:
            return
        tallest = max(tabs.widget(i).sizeHint().height() for i in range(tabs.count()))
        chrome = tabs.sizeHint().height() - tallest     # the tab bar and the frame
        want = max(page.sizeHint().height(), page.minimumSizeHint().height())
        # Fixed, not just capped: Qt's own minimum for a tab widget is its tallest page's.
        if tabs.minimumHeight() != chrome + want or tabs.maximumHeight() != chrome + want:
            tabs.setFixedHeight(chrome + want)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.LayoutRequest:
            try:
                if obj is self.tabs.currentWidget():
                    self.fit()
            except RuntimeError:            # the tab widget is gone (closing)
                pass
        return False


def fit_to_current_tab(tabs: QTabWidget) -> None:
    """Size ``tabs`` by the page it shows, not its tallest page."""
    if tabs.count():
        tabs._fitter = _TabFitter(tabs)


def add_grips(panel: QWidget, key: str) -> List[HeightGrip]:
    """A :class:`HeightGrip` under every list, table and text box in ``panel`` (and each
    widget whose ``grip`` property is set), as the Board panel's net list has; each height
    kept between starts under ``key``. The panel's column, and each tab page's, then keep
    their spare room at the bottom."""
    grips = []
    for n, target in enumerate(_targets(panel)):
        default = target.property("grip_default")
        limits = target.minimumHeight(), target.maximumHeight()
        g = grip(target, f"{key}_height_{n}", target.parentWidget(),
                 int(default) if default else None)
        if not _put_under(g, target):
            target.removeEventFilter(g)
            target._height_grip = None
            target.setMinimumHeight(limits[0])
            target.setMaximumHeight(limits[1])
            g.deleteLater()
            continue
        grips.append(g)
    pack_top(panel.layout())
    for tabs in panel.findChildren(QTabWidget):
        if getattr(tabs, "_height_grip", None) is None:
            fit_to_current_tab(tabs)
        for i in range(tabs.count()):
            page = tabs.widget(i)
            if page is not None and page.layout() is not None:
                pack_top(page.layout())
    return grips
