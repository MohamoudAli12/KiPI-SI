"""The PI plots tab of a DC solve (beside the 3D view in DC mode): the loads against their
tolerances and where each load's drop goes. Drawn by :mod:`kipi.dc.pi.piplots`."""

from __future__ import annotations

import html
from typing import Optional

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from kipi.ac.gui.plot import COLORS
from kipi.dc.pi import piplots
from kipi.si.siplots import Ink

EMPTY = "Solve the power tree in DC mode to see its plots here."
VIEWS = (("loads", "Loads against their tolerance"), ("budget", "Drop budget per load"))
BG = "#1e1e1e"
INK = Ink(COLORS, "#ddd", "#888")


class PIPlot(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure
        self.tree = None
        self.setup = None
        self.figure = Figure(figsize=(6, 3), tight_layout=True)
        self.figure.patch.set_facecolor(BG)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setFocusPolicy(Qt.ClickFocus)
        self.cmb_view = QComboBox(self)
        for key, text in VIEWS:
            self.cmb_view.addItem(text, key)
        self.cmb_view.setToolTip("The plot to show")
        self.cmb_view.currentIndexChanged.connect(lambda _i: self._draw())
        self.lbl = QLabel(EMPTY, self)
        self.lbl.setStyleSheet("color: #999;")
        self.lbl.setWordWrap(True)
        self.lbl.setTextFormat(Qt.RichText)
        self.lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        top = QHBoxLayout()
        top.addWidget(QLabel("Show:"))
        top.addWidget(self.cmb_view, 1)
        try:                               # zoom and pan, as in the other plots
            from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
            self.toolbar = NavigationToolbar2QT(self.canvas, self, coordinates=False)
            top.addWidget(self.toolbar)
        except Exception:                  # noqa: BLE001 — an optional convenience
            self.toolbar = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.addLayout(top)
        lay.addWidget(self.canvas, 1)
        lay.addWidget(self.lbl)
        self.clear()

    # ------------------------------------------------------------------ helpers
    def _style(self, ax=None):
        for a in ([ax] if ax is not None else self.figure.axes):
            a.set_facecolor(BG)
            for s in a.spines.values():
                s.set_color("#888")
            a.tick_params(colors="#ccc", which="both")
            a.xaxis.label.set_color("#ccc")
            a.yaxis.label.set_color("#ccc")
            a.title.set_color("#ddd")
            a.grid(True, color="#444", lw=0.5)

    def _legend(self, ax, **kw):
        if ax.get_legend_handles_labels()[0]:
            leg = ax.legend(fontsize=8, facecolor="#2a2a2a", edgecolor="#555", **kw)
            for t in leg.get_texts():
                t.set_color("#ddd")

    def clear(self):
        self.tree = None
        self.figure.clear()
        self._style(self.figure.add_subplot(111))
        self.lbl.setText(EMPTY)
        self.canvas.draw_idle()

    def set_view(self, key: str):
        i = self.cmb_view.findData(key)
        if i >= 0:
            self.cmb_view.setCurrentIndex(i)

    def set_result(self, tree, setup=None):
        """Show ``tree``, the power-tree result, and ``setup`` it was solved with (for the
        drop budget's series parts)."""
        self.tree, self.setup = tree, setup
        self._draw()

    def save_png(self, path: str):
        self.figure.savefig(path, dpi=150, facecolor=self.figure.get_facecolor())

    # ------------------------------------------------------------------ drawing
    def _draw(self):
        view = self.cmb_view.currentData()
        if self.tree is None:
            return
        self.figure.set_layout_engine("tight")
        text = getattr(self, f"_draw_{view}")(self.tree)
        self.lbl.setText(text)
        self.canvas.draw_idle()

    def _empty(self, message: str) -> str:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self._style(ax)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.text(0.5, 0.5, message, ha="center", va="center", color="#999", fontsize=10,
                transform=ax.transAxes, wrap=True)
        return ""

    def _draw_loads(self, tree) -> str:
        rows = piplots.load_margins(tree)
        if not rows:
            return self._empty("No load has a solved voltage.")
        piplots.draw_loads(self.figure, rows, INK, self._style)
        fails = [r.name for r in rows if r.status == "FAIL"]
        unjudged = sum(r.status is None for r in rows)
        out = (f"<b>{len(rows) - len(fails) - unjudged} of {len(rows)} loads pass</b>"
               if not fails else
               f"<b style='color:#ff6060'>{len(fails)} fail:</b> "
               + html.escape(", ".join(fails)))
        if unjudged:
            out += f"; {unjudged} have no tolerance set (PI_TOL), drawn grey"
        return out

    def _draw_budget(self, tree) -> str:
        rows = piplots.drop_budget(tree, self.setup or getattr(tree, "solved_setup", None))
        if not rows:
            return self._empty("No load has a solved voltage.")
        piplots.draw_budget(self.figure, rows, INK, self._style)
        self._legend(self.figure.axes[0], loc="lower right")
        return ("Each load's drop from its VRM's set voltage, by where it is lost: the VRM "
                "itself (load line; below zero, a remote-sense boost), the series parts on "
                "its path (I × R), the copper (planes, traces and vias) and the ground's "
                "rise. With parallel paths the series parts' share is approximate.")
