"""The Auto-fill power tree dialog: every regulator and source KiPI-SI finds on the board, for
the user to check and change before the setup is filled (kipi_si.dc.pi.importers.tree_autofill).
"""

from __future__ import annotations

import copy
from typing import List, Tuple

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHeaderView,
    QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from kipi_si.core.model.board import BoardSnapshot
from kipi_si.dc.pi.importers.rail_autofill import (
    DEFAULT_MAX_LINK_OHM, PartsLibrary, source_candidates,
)
from kipi_si.dc.pi.importers.tree_autofill import KIND_NAMES, Found
from kipi_si.dc.pi.model import PinRef
from kipi_si.dc.pi.autofill import part_nets
from kipi_si.gui.unit_spin import UnitSpinBox

CHECK_BG = QColor(255, 140, 0, 60)          # a guess to check
MISSING_BG = QColor(220, 50, 50, 70)        # a value the fill needs
COLS = ("Use", "Part", "Type", "Input", "Output", "Voltage", "How it was found")


class TreeAutofillDialog(QDialog):
    """:meth:`choice` is then (the rows as edited, include ground, max link ohms)."""

    def __init__(self, snap: BoardSnapshot, library: PartsLibrary, found: List[Found],
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auto-fill power tree")
        self.snap, self.library = snap, library
        self.rows = [copy.deepcopy(f) for f in found]
        self.values = {f.reference: f.value for f in snap.footprints}
        lay = QVBoxLayout(self)
        intro = QLabel(
            "KiPI-SI found these sources, regulators and switches on the board. Check them, "
            "untick any to leave out, and give each a voltage; OK fills every rail's loads, "
            "series parts and capacitors under them. Orange cells are guesses to check.", self)
        intro.setWordWrap(True)
        lay.addWidget(intro)
        self.table = QTableWidget(len(self.rows), len(COLS), self)
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        hdr = self.table.horizontalHeader()
        for i in range(len(COLS) - 1):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(len(COLS) - 1, QHeaderView.Stretch)
        for i, f in enumerate(self.rows):
            self._fill_row(i, f)
        self.table.itemChanged.connect(lambda it: self._update() if it.column() == 0 else None)
        lay.addWidget(self.table, 1)
        form = QFormLayout()
        self.ground = QCheckBox("Include the ground pins (simulates the ground net too: slower)",
                                self)
        self.max_ohm = UnitSpinBox()
        self.max_ohm.setShownDecimals(3)
        self.max_ohm.setRange(0.0, 1e6)
        self.max_ohm.setSingleStep(0.1)
        self.max_ohm.setSuffix(" Ω")
        self.max_ohm.setValue(DEFAULT_MAX_LINK_OHM)
        self.max_ohm.setToolTip("Resistors up to this value are parts in series (sense "
                                "resistors, 0 Ω links) and are followed; bigger ones are not")
        form.addRow("Follow resistors up to", self.max_ohm)
        form.addRow("", self.ground)
        lay.addLayout(form)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        lay.addWidget(self.buttons)
        self.resize(1100, 160 + 34 * min(len(self.rows), 14))
        self._update()

    # ------------------------------------------------------------------ rows
    def _fill_row(self, i: int, f: Found):
        t = self.table
        use = QTableWidgetItem()
        use.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        use.setCheckState(Qt.Checked if f.use else Qt.Unchecked)
        t.setItem(i, 0, use)
        if f.kind == "source":
            part = QComboBox(t)
            # Not a regulator the rail feeds: that draws from it.
            fed = {r for row in self.rows for r, net in row.feeds() if net == f.rail}
            refs = [r for r in dict.fromkeys([f.ref, *source_candidates(self.snap, f.rail,
                                                                        self.library)])
                    if r == f.ref or r not in fed]
            for r in refs:
                part.addItem(f"{r}  {self.values.get(r, '')}".strip(), r)
            part.setToolTip("The part the rail's power comes in through: an ideal source on "
                            "its pins on the rail")
            part.currentIndexChanged.connect(lambda _x, i=i, c=part: self._part_changed(i, c))
            t.setCellWidget(i, 1, part)
        else:
            t.setItem(i, 1, self._text(f"{f.ref}  {self.values.get(f.ref, '')}".strip()))
        if f.kind == "switch":
            t.setItem(i, 2, self._text(KIND_NAMES["switch"]))
        else:
            kind = QComboBox(t)
            for k in ("source", "ldo", "smps"):
                kind.addItem(KIND_NAMES[k], k)
            kind.setCurrentIndex(kind.findData(f.kind))
            kind.currentIndexChanged.connect(lambda _x, i=i, c=kind: self._kind_changed(i, c))
            t.setCellWidget(i, 2, kind)
        t.setItem(i, 3, self._text(f.input.net if f.input and f.kind != "source" else "–"))
        t.setItem(i, 4, self._text(f.rail))
        if f.kind == "switch":
            t.setItem(i, 5, self._text("–"))
        else:
            volts = QDoubleSpinBox(t)
            volts.setRange(0.0, 1000.0)
            volts.setDecimals(3)
            volts.setSuffix(" V")
            volts.setSpecialValueText("set it")
            volts.setValue(f.voltage or 0.0)
            volts.setToolTip(f"From its {f.voltage_from}" if f.voltage_from else
                             "Not on the part (PI_V), in the library or in the rail's name")
            volts.valueChanged.connect(lambda v, i=i: self._volts_changed(i, v))
            t.setCellWidget(i, 5, volts)
        how = self._text(f.why + (f". Check: {f.check}" if f.check else ""))
        how.setToolTip(how.text())
        t.setItem(i, 6, how)
        self._shade(i)

    def _text(self, text: str) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemIsEnabled)
        return it

    def _shade(self, i: int):
        f = self.rows[i]
        for col in (1, 6):
            it = self.table.item(i, col)
            if it is not None:
                it.setBackground(CHECK_BG if f.check else QColor(0, 0, 0, 0))
        w = self.table.cellWidget(i, 1)
        if w is not None:
            w.setStyleSheet("QComboBox { background: rgba(255,140,0,60); }" if f.check else "")
        v = self.table.cellWidget(i, 5)
        if v is not None:
            v.setStyleSheet("" if f.voltage else "QDoubleSpinBox { background: rgba(220,50,50,70); }")

    def _part_changed(self, i: int, combo: QComboBox):
        f = self.rows[i]
        ref = combo.currentData()
        f.ref = ref
        f.output = PinRef(ref, f.rail, list(part_nets(self.snap, ref).get(f.rail, [])))
        f.ground = None
        f.check = ""
        self._shade(i)

    def _kind_changed(self, i: int, combo: QComboBox):
        f = self.rows[i]
        f.kind = combo.currentData()
        if f.kind != "source" and f.input is None:
            f.check = "no input rail: set its input pins on the VRMs tab"
        self.table.item(i, 3).setText(f.input.net if f.input and f.kind != "source" else "–")
        self._update()

    def _volts_changed(self, i: int, v: float):
        self.rows[i].voltage = v or None
        self._shade(i)
        self._update()

    def _update(self):
        missing = [f.ref for i, f in enumerate(self.rows) if self._used(i)
                   and f.kind != "switch" and not f.voltage]
        n = sum(self._used(i) for i in range(len(self.rows)))
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(n > 0 and not missing)
        self.status.setText(f"Give {', '.join(missing)} a voltage." if missing else
                            f"{n} of {len(self.rows)} in use.")
        self.status.setStyleSheet("color: #d04040;" if missing else "color: #999;")

    def _used(self, i: int) -> bool:
        it = self.table.item(i, 0)
        return it is not None and it.checkState() == Qt.Checked

    def accept(self):
        for i, f in enumerate(self.rows):
            f.use = self._used(i)
        super().accept()

    def choice(self) -> Tuple[List[Found], bool, float]:
        for i, f in enumerate(self.rows):
            f.use = self._used(i)
        return self.rows, self.ground.isChecked(), float(self.max_ohm.value())
