"""The Board map tab (#67): a top-down view of an AC solve, as in its HTML report. The solver's
mesh of the rail and its ground (one copper layer, or all of them), the board outline, the
probes, and the capacitors in the model (one colour per model) and those left out. It fills
in while the rail solves: the parts first, then the mesh."""

from __future__ import annotations

from typing import List, Optional

import numpy as np
from qtpy.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from kipi.ac.board_map import ACMap, nets_text
from kipi.ac.gui.plot import COLORS

EMPTY = "Solve a rail in AC mode to see its mesh, capacitors and probes here."
HINT = "Hover a part for its model."
RAIL_COLOR = "#b98a5c"         # opaque: see-through triangles show seams
GROUND_COLOR = "#4a6178"
ALL_LAYERS = -1
HOVER_PX = 8                       # how near the pointer must be to a part


class BoardMap(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure
        self.figure = Figure(figsize=(6, 4), tight_layout=True)
        self.figure.patch.set_facecolor("#1e1e1e")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.lbl = QLabel(EMPTY, self)
        self.lbl.setStyleSheet("color: #999;")
        self.lbl.setWordWrap(True)
        self.cmb_layer = QComboBox(self)
        self.cmb_layer.setToolTip("The copper layer whose mesh is shown")
        self.cmb_layer.currentIndexChanged.connect(self._redraw)
        self.chk_mesh = QCheckBox("Mesh edges", self)
        self.chk_mesh.setChecked(True)
        self.chk_mesh.setToolTip("Draw the edges of the solver's triangles; untick to see "
                                 "the copper alone")
        self.chk_mesh.toggled.connect(self._show_edges)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        top = QHBoxLayout()
        top.addWidget(QLabel("Layer", self))
        top.addWidget(self.cmb_layer)
        top.addWidget(self.chk_mesh)
        top.addStretch(1)
        lay.addLayout(top)
        lay.addWidget(self.lbl)
        lay.addWidget(self.canvas, 1)
        # Else the controls set the main window's minimum width (it must fit small screens).
        self.setMinimumWidth(120)
        self.canvas.mpl_connect("motion_notify_event", self._hover)
        self.canvas.mpl_connect("draw_event", self._drawn)
        self.board_map: Optional[ACMap] = None
        self._parts: List[tuple] = []          # (x, y, text) of every part drawn
        self._annot = None
        self._layer_ids: List[int] = []
        self._mesh_pcs: List = []              # the mesh's copper, rail and ground
        # The view never zooms or pans: each drawing of it (mesh edges on or off, at a
        # canvas size) is kept, so the edges toggle and hovering need no redraw of a large
        # mesh, which takes seconds.
        self._backgrounds: dict = {}
        self._style()
        self._fill_layers()
        self.canvas.draw_idle()

    def _style(self):
        ax = self.ax
        ax.set_facecolor("#1e1e1e")
        for s in ax.spines.values():
            s.set_color("#888")
        ax.tick_params(colors="#ccc", which="both")
        ax.xaxis.label.set_color("#ccc")
        ax.yaxis.label.set_color("#ccc")
        ax.title.set_color("#ddd")

    # ------------------------------------------------------------------ data
    def clear(self):
        self.board_map = None
        self._parts = []
        self._fill_layers()
        self.lbl.setText(EMPTY)
        self.ax.clear()
        self._annot = None
        self._mesh_pcs = []
        self._backgrounds = {}
        self._style()
        self.canvas.draw_idle()

    def set_map(self, board_map: Optional[ACMap]):
        """Show ``board_map`` (None clears the view). Called again as the solve meshes."""
        if board_map is None:
            self.clear()
            return
        self.board_map = board_map
        self._fill_layers()
        self._redraw()

    def _fill_layers(self):
        """The layer choice: every layer the mesh is on, keeping the choice made."""
        m = self.board_map
        layers = m.mesh_layers() if m is not None else []
        ids = [ALL_LAYERS] + [i for i, _ in layers]
        if ids == self._layer_ids:
            return
        keep = self.cmb_layer.currentData()
        self.cmb_layer.blockSignals(True)
        self.cmb_layer.clear()
        self.cmb_layer.addItem("All layers", ALL_LAYERS)
        for i, name in layers:
            self.cmb_layer.addItem(name, i)
        k = self.cmb_layer.findData(keep)
        self.cmb_layer.setCurrentIndex(max(k, 0))
        self.cmb_layer.blockSignals(False)
        self.cmb_layer.setEnabled(bool(layers))
        self._layer_ids = ids

    # ------------------------------------------------------------------ drawing
    def _redraw(self, *_args):
        """Draw the map, always fitted to the board: the view is fixed, with no zoom or pan."""
        m = self.board_map
        if m is None:
            return
        from matplotlib.collections import PolyCollection
        ax = self.ax
        ax.clear()
        self._annot = None
        self._mesh_pcs = []
        self._backgrounds = {}
        self._style()
        mesh = m.mesh
        layer = self.cmb_layer.currentData()
        if mesh is not None and len(mesh.tris):
            keep = np.ones(len(mesh.tris), bool) if layer in (None, ALL_LAYERS) \
                else mesh.tri_layer == layer
            # Ground first, so the rail's copper shows on top of a ground plane.
            for ground, color, label in ((True, GROUND_COLOR, m.ground),
                                         (False, RAIL_COLOR, nets_text(m.rail_nets))):
                sel = keep & (mesh.tri_ground == ground)
                if not sel.any():
                    continue
                pc = PolyCollection(mesh.points[mesh.tris[sel]], facecolors=color,
                                    label=label, zorder=1 if ground else 2)
                ax.add_collection(pc)
                self._mesh_pcs.append(pc)
            self._style_edges()
        for r in m.outline:
            ax.plot(r[:, 0], r[:, 1], color="#aaa", lw=1.0, zorder=3)
        self._parts = []
        for k, (name, parts) in enumerate(m.models.items()):
            self._scatter(parts, f"{name} ({len(parts)})", marker="o", s=36,
                          color=COLORS[k % len(COLORS)], edgecolors="#111")
        if m.missing:
            self._scatter(m.missing, f"no model, left out ({len(m.missing)})", marker="x",
                          s=60, color="#f0f0f0", linewidths=1.6)
        if m.probes:
            self._scatter(m.probes, "probes", marker="*", s=180, color="#ff4040",
                          edgecolors="#600")
            for p in m.probes:
                ax.annotate(p.ref, (p.x, p.y), xytext=(0, 9), textcoords="offset points",
                            ha="center", color="#ffb0b0", fontsize=8, zorder=6)
        ax.set_aspect("equal", adjustable="box")
        self._fit()
        ax.set_xlabel("x (mm)")
        ax.set_ylabel("y (mm)")
        where = ("all layers" if layer in (None, ALL_LAYERS) else m.layer_name(layer))
        ax.set_title(f"{m.rail}: {nets_text(m.rail_nets)} against {m.ground}"
                     + (f"\nmesh on {where}" if mesh is not None else "\nmeshing…"),
                     fontsize=10)
        handles, _ = ax.get_legend_handles_labels()
        if handles:
            # Below the board, as in the report: at its side, long labels squeezed the map.
            leg = ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3,
                            fontsize=8, facecolor="#2a2a2a", edgecolor="#555")
            for t in leg.get_texts():
                t.set_color("#ddd")
        self.lbl.setText(HINT)
        self.canvas.draw_idle()

    def _style_edges(self):
        """The mesh's triangles with their edges, or without: then unsmoothed, which draws
        in half the time and leaves no seams between them."""
        edges = self.chk_mesh.isChecked()
        for pc in self._mesh_pcs:
            pc.set_edgecolor("#111" if edges else "none")
            pc.set_linewidth(0.2 if edges else 0.0)
            pc.set_antialiased(edges)

    def _show_edges(self, *_args):
        self._style_edges()
        bg = self._backgrounds.get(self._view_key())
        if bg is None:
            self.canvas.draw_idle()
        else:                                  # drawn before: show that drawing again
            self.canvas.restore_region(bg)
            self._blit_annot()

    def _view_key(self):
        return self.chk_mesh.isChecked(), self.canvas.get_width_height()

    def _drawn(self, _event):
        """Keep each full drawing (without the hover label, which is drawn over it)."""
        if self.board_map is not None:
            self._backgrounds[self._view_key()] = self.canvas.copy_from_bbox(self.figure.bbox)
            if self._annot is not None and self._annot.get_visible():
                self.ax.draw_artist(self._annot)    # the full draw then shows it

    def _blit_annot(self):
        if self._annot is not None and self._annot.get_visible():
            self.ax.draw_artist(self._annot)
        self.canvas.blit(self.figure.bbox)

    def _scatter(self, parts, label, **kw):
        xs = [p.x for p in parts]
        ys = [p.y for p in parts]
        kw.setdefault("linewidths", 0.6)
        self.ax.scatter(xs, ys, label=label, zorder=5, **kw)
        self._parts += [(p.x, p.y, p.text) for p in parts]

    def _fit(self):
        ext = self.board_map.extent() if self.board_map is not None else None
        if ext is None:
            return
        x0, x1, y0, y1 = ext
        pad = 0.03 * max(x1 - x0, y1 - y0, 1.0)
        self.ax.set_xlim(x0 - pad, x1 + pad)
        self.ax.set_ylim(y1 + pad, y0 - pad)       # KiCad's y points down

    # ------------------------------------------------------------------ mouse
    def _hover(self, event):
        text = self._part_at(event)
        if self._annot is None:
            self._annot = self.ax.annotate(
                "", (0, 0), xytext=(10, 10), textcoords="offset points", fontsize=8,
                color="#eee", zorder=10, animated=True,      # drawn by _blit_annot
                bbox=dict(boxstyle="round", fc="#2a2a2a", ec="#777"))
            self._annot.set_visible(False)
        if text is None:
            if self._annot.get_visible():
                self._annot.set_visible(False)
                self._repaint_annot()
            return
        x, y, t = text
        if self._annot.get_visible() and self._annot.get_text() == t:
            return
        self._annot.xy = (x, y)
        self._annot.set_text(t)
        self._annot.set_visible(True)
        self._repaint_annot()

    def _repaint_annot(self):
        """The hover label over the kept drawing; a full draw if there is none yet."""
        bg = self._backgrounds.get(self._view_key())
        if bg is None:
            self.canvas.draw_idle()
            return
        self.canvas.restore_region(bg)
        self._blit_annot()

    def _part_at(self, event):
        if not self._parts or event.inaxes is not self.ax or event.x is None:
            return None
        xy = self.ax.transData.transform([(x, y) for x, y, _ in self._parts])
        d = np.hypot(xy[:, 0] - event.x, xy[:, 1] - event.y)
        k = int(np.argmin(d))
        return self._parts[k] if d[k] <= HOVER_PX else None

    def save_png(self, path: str):
        self.figure.savefig(path, dpi=150, facecolor=self.figure.get_facecolor())
