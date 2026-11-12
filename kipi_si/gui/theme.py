"""Dark or light widgets. Dark unless the user picks light with the toolbar's Dark mode
button; the choice is kept in KiPI-SI's QSettings.

KiPI-SI draws with Qt's Fusion style, which takes its colours from the application palette:
dark mode sets one here, and light mode puts back the palette Qt started with (the
system's). The power tree keeps its light canvas; everything else follows the switch: what
reads the palette (the 3D view, tooltip drawings, the stackup view, the spinner) and the
plots (:mod:`kipi_si.gui.plot_theme`).
"""

from __future__ import annotations

import weakref
from typing import Optional

from qtpy.QtCore import QSettings, Qt
from qtpy.QtGui import QColor, QPainter, QPalette, QPen
from qtpy.QtWidgets import QApplication, QProxyStyle, QStyle, QWidget

DARK, LIGHT = "dark", "light"
DEFAULT = DARK
_KEY = "appearance/theme"

_startup: Optional[QPalette] = None       # the palette Qt started with, for light mode
_style: Optional["_IndicatorStyle"] = None   # kept: Qt does not own a Python style

# Each mode's Solve button: green, so the action the setup leads to stands out (grey while
# it cannot be pressed).
SOLVE_BUTTON_STYLE = (
    "QPushButton { font-weight: bold; padding: 6px 14px; color: white; "
    "background: #2e8b3e; border: 1px solid #1f6b2c; border-radius: 4px; }"
    "QPushButton:hover { background: #37a34a; }"
    "QPushButton:pressed { background: #23702f; }"
    "QPushButton:disabled { color: palette(mid); background: palette(button); "
    "border: 1px solid palette(mid); }")


def _settings() -> QSettings:
    return QSettings("KiPI-SI", "KiPI-SI")


def saved() -> str:
    """The theme chosen last, else the default."""
    value = str(_settings().value(_KEY, DEFAULT) or DEFAULT).lower()
    return value if value in (DARK, LIGHT) else DEFAULT


def dark_palette() -> QPalette:
    """A dark Fusion palette, close to the plots' #1e1e1e background."""
    window, base, alt = QColor("#28292c"), QColor("#1e1f22"), QColor("#25262a")
    text, dim, accent = QColor("#e3e3e6"), QColor("#8b8d93"), QColor("#3b82d6")
    pal = QPalette()
    for role, color in (
            (QPalette.Window, window), (QPalette.WindowText, text),
            (QPalette.Base, base), (QPalette.AlternateBase, alt),
            (QPalette.ToolTipBase, QColor("#3a3a3a")), (QPalette.ToolTipText, text),
            (QPalette.PlaceholderText, dim), (QPalette.Text, text),
            (QPalette.Button, QColor("#34363a")), (QPalette.ButtonText, text),
            (QPalette.BrightText, QColor("#ff6b6b")),
            (QPalette.Light, QColor("#4a4c51")), (QPalette.Midlight, QColor("#3d3f44")),
            (QPalette.Mid, QColor("#505258")), (QPalette.Dark, QColor("#18191b")),
            (QPalette.Shadow, QColor("#000000")),
            (QPalette.Highlight, accent), (QPalette.HighlightedText, QColor("#ffffff")),
            (QPalette.Link, QColor("#6ab0f3")), (QPalette.LinkVisited, QColor("#b18cf0"))):
        pal.setColor(role, color)
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, dim)
    pal.setColor(QPalette.Disabled, QPalette.Base, window)
    pal.setColor(QPalette.Disabled, QPalette.Highlight, QColor("#4a4a4a"))
    return pal


class _IndicatorStyle(QProxyStyle):
    """Fusion with a light outline round check boxes and radio buttons in dark mode:
    Fusion outlines them in a shade of the window colour, next to invisible on a dark
    window."""

    dark = False
    _BOXES = (QStyle.PE_IndicatorCheckBox, QStyle.PE_IndicatorItemViewItemCheck)

    def drawPrimitive(self, element, option, painter, widget=None):
        super().drawPrimitive(element, option, painter, widget)
        radio = element == QStyle.PE_IndicatorRadioButton
        if not self.dark or not (radio or element in self._BOXES):
            return
        r = option.rect.adjusted(1, 1, -2, -2) if radio else option.rect.adjusted(0, 0, -1, -1)
        if r.width() < 4 or r.height() < 4:
            return                      # a hidden indicator (the mode switch's)
        on = bool(option.state & QStyle.State_Enabled)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, radio)
        painter.setPen(QPen(QColor("#f0f0f0" if on else "#808080"), 1))
        painter.setBrush(Qt.NoBrush)
        if radio:
            painter.drawEllipse(r)
        else:
            painter.drawRoundedRect(r, 2, 2)
        painter.restore()


def _mix(a: QColor, b: QColor, t: float) -> str:
    """``a`` moved ``t`` (0..1) of the way to ``b``, as #rrggbb."""
    return QColor(round(a.red() + (b.red() - a.red()) * t),
                  round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t)).name()


def stylesheet(pal: QPalette) -> str:
    """The application's style sheet, its colours taken from ``pal``: rounded buttons,
    underlined tabs, slim scroll bars, quiet group boxes and docks. Inputs (spin boxes,
    combo boxes) keep Fusion's drawing, which the palette already colours."""
    c = pal.color
    window, base = c(QPalette.Window), c(QPalette.Base)
    text, button = c(QPalette.WindowText), c(QPalette.Button)
    accent = c(QPalette.Highlight)
    dim = c(QPalette.Disabled, QPalette.WindowText).name()
    dark = window.lightness() < 128
    border = _mix(window, text, 0.16 if dark else 0.22)
    hover = _mix(button, text, 0.08)
    pressed = _mix(button, text, 0.14)
    header = _mix(window, base, 0.5)
    title = _mix(window, text, 0.55)
    handle = _mix(window, text, 0.25)
    soft = _mix(window, accent, 0.25)
    return f"""
QToolBar {{ background: {window.name()}; border: none; border-bottom: 1px solid {border};
           padding: 4px 6px; spacing: 2px; }}
QToolBar::separator {{ width: 1px; background: {border}; margin: 6px 8px; }}
QToolBar QToolButton {{ border: 1px solid transparent; border-radius: 6px; padding: 4px 7px;
                       background: transparent; }}
QToolBar QToolButton:hover {{ background: {hover}; border-color: {border}; }}
QToolBar QToolButton:pressed {{ background: {pressed}; }}
QToolBar QToolButton:checked {{ background: {soft}; border-color: {border}; }}
QToolBar QToolButton[popupMode="1"] {{ padding-right: 18px; }}
QToolBar QToolButton::menu-button {{ border: none; width: 16px; }}
QToolBar QLabel#toolbar_group {{ color: {title}; font-size: 8pt; padding: 0 2px 0 4px; }}

QPushButton {{ background: {button.name()}; border: 1px solid {border}; border-radius: 5px;
              padding: 4px 12px; min-height: 18px; }}
QPushButton:hover {{ background: {hover}; }}
QPushButton:pressed {{ background: {pressed}; }}
QPushButton:checked {{ background: {soft}; }}
QPushButton:disabled {{ color: {dim}; background: {window.name()}; }}
QPushButton[primary="true"] {{ background: {accent.name()}; color: white;
                              border-color: {_mix(accent, QColor('black'), 0.25)};
                              font-weight: bold; }}
QPushButton[primary="true"]:hover {{ background: {_mix(accent, QColor('white'), 0.12)}; }}
QPushButton[primary="true"]:disabled {{ color: {dim}; background: {window.name()};
                                       border-color: {border}; }}
QPushButton::menu-indicator {{ subcontrol-origin: padding; subcontrol-position: right center;
                              right: 4px; }}

QTabWidget::pane {{ border: 1px solid {border}; border-radius: 6px; top: -1px; }}
QTabWidget[documentMode="true"]::pane {{ border: none; }}
QTabBar::tab {{ background: transparent; border: none; border-bottom: 2px solid transparent;
               padding: 6px 10px; margin-right: 2px; color: {title}; }}
QTabBar::tab:hover {{ color: {text.name()}; border-bottom-color: {border}; }}
QTabBar::tab:selected {{ color: {text.name()}; border-bottom-color: {accent.name()}; }}
QTabBar::tab:disabled {{ color: {dim}; }}

QGroupBox {{ border: 1px solid {border}; border-radius: 6px; margin-top: 16px;
            padding: 8px 4px 4px 4px; font-weight: bold; }}
QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 8px;
                   padding: 0 4px; color: {title}; }}

QDockWidget::title {{ background: {header}; padding: 6px 8px; text-align: left;
                     border-bottom: 1px solid {border}; }}
QMainWindow::separator {{ background: {border}; width: 1px; height: 1px; }}
QMainWindow::separator:hover {{ background: {accent.name()}; }}

QListWidget, QTreeView, QTableView, QTextBrowser, QPlainTextEdit {{
    border: 1px solid {border}; border-radius: 5px; }}
QListWidget::item {{ padding: 2px 4px; border-radius: 4px; }}
QListWidget::item:hover:!selected {{ background: {hover}; }}
QListWidget::item:selected {{ background: {accent.name()}; color: {c(QPalette.HighlightedText).name()}; }}
QHeaderView::section {{ background: {header}; border: none; border-right: 1px solid {border};
                       border-bottom: 1px solid {border}; padding: 4px 6px; }}
QLineEdit {{ border: 1px solid {border}; border-radius: 5px; padding: 4px 6px;
            background: {base.name()}; }}
QLineEdit:focus {{ border-color: {accent.name()}; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle {{ background: {handle}; border-radius: 3px; }}
QScrollBar::handle:hover {{ background: {_mix(window, text, 0.4)}; }}
QScrollBar::handle:vertical {{ min-height: 24px; }}
QScrollBar::handle:horizontal {{ min-width: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QMenu {{ background: {base.name()}; border: 1px solid {border}; border-radius: 6px;
        padding: 4px; }}
QMenu::item {{ padding: 5px 22px 5px 12px; border-radius: 4px; }}
QMenu::item:selected {{ background: {accent.name()}; color: white; }}
QMenu::item:disabled {{ color: {dim}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 4px 6px; }}
QToolTip {{ background: {c(QPalette.ToolTipBase).name()}; color: {c(QPalette.ToolTipText).name()};
           border: 1px solid {border}; border-radius: 5px; padding: 5px; }}
QStatusBar {{ color: {title}; border-top: 1px solid {border}; }}
QProgressBar {{ border: none; border-radius: 3px; background: {_mix(window, text, 0.1)}; }}
QProgressBar::chunk {{ border-radius: 3px; background: {accent.name()}; }}
"""


def _indicator_style(app: QApplication) -> "_IndicatorStyle":
    """The proxy style, set on ``app`` once. Once a style sheet is on, ``app.style()`` is
    Qt's style-sheet style wrapping ours, so it is looked up in ``_style``: setting a style
    again would re-polish every widget."""
    global _style
    if _style is None or (not app.styleSheet() and app.style() is not _style):
        _style = _IndicatorStyle(app.style().name())
        app.setStyle(_style)
    return _style


# Tooltips are windows of their own, outside any window that :func:`adopt` styled; this
# sheet is set on the application once and reads only the palette, so a tooltip made after
# a switch takes the new colours without the whole application being re-polished.
_APP_SHEET = ("QToolTip { color: palette(tooltip-text); background: palette(tooltip-base); "
              "border: 1px solid palette(mid); border-radius: 5px; padding: 5px; }")

_windows: "weakref.WeakSet" = weakref.WeakSet()


def adopt(window: QWidget) -> None:
    """Style ``window`` and everything in it (its dialogs, menus and docks included) with
    :func:`stylesheet`, now and on every switch.

    The sheet goes on the window, not the application: Qt re-polishes every widget of the
    application when its sheet changes, several seconds on a full window, against a
    fraction of a second for one window's own."""
    _windows.add(window)
    window.setStyleSheet(stylesheet(QApplication.instance().palette()))


def apply(name: Optional[str] = None, app: Optional[QApplication] = None) -> str:
    """Show ``name`` (default: the saved theme) on ``app``; returns the theme shown."""
    global _startup
    app = app or QApplication.instance()
    name = name or saved()
    if _startup is None:
        _startup = QPalette(app.palette())
    _indicator_style(app).dark = name == DARK
    from kipi_si.gui import plot_theme
    plot_theme.use(name == DARK)          # before the palette: the plots redraw on its change
    app.setPalette(dark_palette() if name == DARK else _startup)
    if app.styleSheet() != _APP_SHEET:
        app.setStyleSheet(_APP_SHEET)
    sheet = stylesheet(app.palette())
    for window in list(_windows):
        window.setStyleSheet(sheet)
    from kipi_si.gui import icons
    icons.retint()
    # A widget with its own style sheet (the bold Solve buttons, the log's monospace
    # font) took its colours when it was first shown and ignores a new palette; setting
    # the sheet again makes it take them afresh.
    for w in app.allWidgets():
        if w in _windows:
            continue
        sheet = w.styleSheet()
        if sheet:
            w.setStyleSheet(sheet)
    return name


def choose(name: str) -> None:
    """Show ``name`` and keep it for the next start."""
    _settings().setValue(_KEY, apply(name))
