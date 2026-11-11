"""The whole power tree found on the board: switchers, LDOs, switches and sources."""

import pytest

from kipi_si.core.model.board import Footprint, Net, Pad
from kipi_si.dc.pi.autofill import input_net
from kipi_si.dc.pi.importers.rail_autofill import (
    AutofillError, PartsLibrary, autofill_rail, source_candidates, vrm_kind,
)
from kipi_si.dc.pi.importers.tree_autofill import autofill_tree, find_tree
from kipi_si.dc.pi.model import PISetup, validate
from kipi_si.noise.checks import seed_phases, switching_frequency
from synthetic import make_board

PARTS = {  # ref: (value, fields)
    "J1": ("CONN", {}),
    "U1": ("BUCK", {"PI_FSW": "600kHz"}), "L1": ("1u", {}),
    "U2": ("LDO18", {}), "U3": ("MCU", {"PI_I": "50mA"}),
    "U4": ("TRANSLATOR", {}), "U5": ("SENSOR", {"PI_I": "10mA"}),
    "U8": ("BOOST", {}), "L2": ("2u2", {}), "U9": ("DRIVER", {"PI_I": "100mA"}),
    "Q1": ("PFET", {}), "U6": ("LDO12", {}), "U10": ("CORE", {"PI_I": "200mA"}),
    "R1": ("10k", {}), "R2": ("3k3", {}), "R7": ("100k", {}), "R8": ("100k", {}),
    "R5": ("50k", {}), "R6": ("10k", {}),
    "R9": ("0R", {}),
    "C1": ("10u", {}), "C2": ("22u", {}), "C3": ("1u", {}), "C4": ("100n", {}),
    "C5": ("22u", {}), "C6": ("1u", {}), "C7": ("1u", {}), "CB": ("100n", {}),
}
PINS = [  # (ref, pin, net)
    ("J1", "1", "VIN"), ("J1", "2", "GND"),
    ("C1", "1", "VIN"), ("C1", "2", "GND"),
    # The buck: VIN in, SW through L1 to +3V3, its FB divider from +3V3, and an enable
    # pull-up from VIN (not its feedback), all on nets named like rails.
    ("U1", "1", "VIN"), ("U1", "2", "VIN"), ("U1", "3", "3V3_SW"), ("U1", "4", "3V3_FB"),
    ("U1", "5", "3V3_EN"), ("U1", "6", "3V3_BOOT"), ("U1", "7", "GND"), ("U1", "8", "GND"),
    ("L1", "1", "3V3_SW"), ("L1", "2", "+3V3"),
    ("CB", "1", "3V3_BOOT"), ("CB", "2", "3V3_SW"),
    ("R1", "1", "+3V3"), ("R1", "2", "3V3_FB"), ("R2", "1", "3V3_FB"), ("R2", "2", "GND"),
    ("R7", "1", "VIN"), ("R7", "2", "3V3_EN"), ("R8", "1", "3V3_EN"), ("R8", "2", "GND"),
    ("C2", "1", "+3V3"), ("C2", "2", "GND"),
    # The LDO, and loads on its rail and the buck's.
    ("U2", "1", "+3V3"), ("U2", "2", "+1V8"), ("U2", "3", "GND"),
    ("C3", "1", "+1V8"), ("C3", "2", "GND"),
    ("U3", "1", "+1V8"), ("U3", "2", "GND"), ("U3", "3", "A1"), ("U3", "4", "A2"),
    ("U5", "1", "+3V3"), ("U5", "2", "GND"), ("U5", "3", "B1"), ("U5", "4", "B2"),
    # A level translator on both rails: a load on each, not a regulator.
    ("U4", "1", "+1V8"), ("U4", "2", "+3V3"), ("U4", "3", "GND"),
    ("U4", "4", "A1"), ("U4", "5", "A2"), ("U4", "6", "B1"), ("U4", "7", "B2"),
    ("C4", "1", "+1V8"), ("C4", "2", "GND"),
    # A boost from +3V3: L2 to its switch node, out on +5V with its divider from there.
    ("U8", "1", "SW2"), ("U8", "2", "+5V"), ("U8", "3", "FB2"), ("U8", "4", "GND"),
    ("L2", "1", "+3V3"), ("L2", "2", "SW2"),
    ("R5", "1", "+5V"), ("R5", "2", "FB2"), ("R6", "1", "FB2"), ("R6", "2", "GND"),
    ("C5", "1", "+5V"), ("C5", "2", "GND"),
    ("U9", "1", "+5V"), ("U9", "2", "GND"),
    # A P-FET switching +3V3 on to +3V3_P, which feeds a second LDO.
    ("Q1", "1", "P_EN"), ("Q1", "2", "+3V3"), ("Q1", "3", "+3V3_P"),
    ("C6", "1", "+3V3_P"), ("C6", "2", "GND"),
    ("U6", "1", "+3V3_P"), ("U6", "2", "+1V2"), ("U6", "3", "GND"),
    ("C7", "1", "+1V2"), ("C7", "2", "GND"),
    ("U10", "1", "+1V2"), ("U10", "2", "GND"),
    # A strap not fitted, between the rails.
    ("R9", "1", "+1V8"), ("R9", "2", "+3V3"),
]
DNP = {"R9"}


def board(parts=None, pins=(), dnp=DNP):
    parts, pins = {**PARTS, **(parts or {})}, [*PINS, *pins]
    snap = make_board()
    snap.pads, snap.footprints, snap.zones = [], [], []
    names = sorted({n for _, _, n in pins})
    snap.nets = [Net(0, "")] + [Net(i + 1, n) for i, n in enumerate(names)]
    for i, (ref, pin, net) in enumerate(pins):
        snap.pads.append(Pad(f"p{i}", net, ref, pin, (float(i), 0.0), "smd"))
    for ref, (value, fields) in parts.items():
        ids = [p.id for p in snap.pads if p.footprint == ref]
        snap.footprints.append(Footprint(f"f{ref}", ref, value, (float(len(ids)), 0.0), "top",
                                         ids, fields=dict(fields), dnp=ref in dnp))
    snap.project_dir = ""
    snap.invalidate_index()
    return snap


def by_ref(found):
    return {f.ref: f for f in found}


def test_input_rail_skips_the_regulators_own_nets():
    # 3V3_FB, 3V3_EN and 3V3_BOOT are named like rails, but only U1 and passives are on
    # them: VIN is its input.
    assert input_net(board(), "U1", ["+3V3", "GND"]) == "VIN"


def test_finds_the_tree():
    f = by_ref(find_tree(board(), PartsLibrary()))
    assert set(f) == {"J1", "U1", "U2", "U8", "Q1", "U6"}
    buck = f["U1"]
    assert (buck.kind, buck.input.net, buck.rail) == ("smps", "VIN", "+3V3")
    assert buck.output.ref == "L1"                  # the inductor's pins on the rail
    assert buck.inductors == ["L1"] and buck.switch_nets == ["3V3_SW"]
    assert buck.ground.net == "GND" and "buck" in buck.why and not buck.check
    assert buck.voltage == pytest.approx(3.3) and buck.voltage_from == "net name"
    assert buck.fsw_hz == pytest.approx(600e3)
    boost = f["U8"]
    assert (boost.kind, boost.rail, boost.output.ref) == ("smps", "+5V", "U8")
    assert (boost.input.ref, boost.input.net) == ("L2", "+3V3") and "boost" in boost.why
    ldo = f["U2"]
    assert (ldo.kind, ldo.input.net, ldo.rail) == ("ldo", "+3V3", "+1V8")
    sw = f["Q1"]
    assert (sw.kind, sw.input.net, sw.rail) == ("switch", "+3V3", "+3V3_P")
    src = f["J1"]
    assert (src.kind, src.rail, src.voltage, src.check) == ("source", "VIN", None, "")
    assert "U4" not in f                            # a translator: a load on both rails
    # Sources first, then down the tree.
    order = [x.ref for x in find_tree(board(), PartsLibrary())]
    assert order.index("U1") < order.index("U2") and order[0] == "J1"


def test_fills_the_tree():
    snap = board()
    found = find_tree(snap, PartsLibrary())
    by_ref(found)["J1"].voltage = 12.0
    res = autofill_tree(snap, found, PISetup(), PartsLibrary())
    s = res.setup
    assert validate(s) == []
    kinds = {v.output.net: v.kind for v in s.vrms}
    assert kinds == {"VIN": "source", "+3V3": "smps", "+1V8": "ldo", "+5V": "smps",
                     "+1V2": "ldo"}
    loads = {(l.supply.ref, l.supply.net) for l in s.loads}
    # Regulators are not loads on the rails feeding them; the translator is on both.
    assert not {("U1", "VIN"), ("U2", "+3V3"), ("U8", "+3V3"), ("U6", "+3V3_P")} & loads
    assert {("U4", "+1V8"), ("U4", "+3V3"), ("U3", "+1V8"), ("U10", "+1V2")} <= loads
    links = {(k.side_a.ref, k.side_a.net, k.side_b.net) for k in s.links}
    assert ("Q1", "+3V3", "+3V3_P") in links       # the switch, as a DC connection
    assert not any(k.side_a.ref == "R9" for k in s.links)   # not fitted
    assert any("DNP" in n and "R9" in n for n in res.notes)
    vin = next(v for v in s.vrms if v.kind == "source")
    assert vin.voltage == 12.0 and vin.output.ref == "J1"


def test_unticked_rows_and_a_changed_type():
    snap = board()
    found = find_tree(snap, PartsLibrary())
    f = by_ref(found)
    f["J1"].voltage = 12.0
    f["U8"].use = False
    f["U2"].kind = "source"
    s = autofill_tree(snap, found, PISetup(), PartsLibrary()).setup
    assert "+5V" not in {v.output.net for v in s.vrms}
    ldo = next(v for v in s.vrms if v.output.net == "+1V8")
    assert ldo.kind == "source" and ldo.input is None


def test_replaces_a_wrong_source_on_a_rail():
    snap = board()
    found = find_tree(snap, PartsLibrary())
    by_ref(found)["J1"].voltage = 12.0
    # A first try made the translator the source of +1V8.
    first = autofill_rail(snap, "+1V8", "U4", PISetup(), PartsLibrary()).setup
    assert first.vrms[0].output.ref == "U4"
    s = autofill_tree(snap, found, first, PartsLibrary()).setup
    assert [v.output.ref for v in s.vrms if v.output.net == "+1V8"] == ["U2"]


def test_auto_fill_rail_makes_a_recognised_switcher():
    snap = board()
    res = autofill_rail(snap, "+3V3", "U1", PISetup(), PartsLibrary())
    v = res.setup.vrms[0]
    assert (v.kind, v.input.net, v.output.ref) == ("smps", "VIN", "L1")
    # Filling its input rail after: the switcher is not a load on it.
    s = autofill_rail(snap, "VIN", "J1", res.setup, PartsLibrary()).setup
    assert not any(l.supply.ref == "U1" for l in s.loads)


def test_source_candidates_skip_translators_and_fed_regulators():
    snap = board()
    lib = PartsLibrary()
    assert source_candidates(snap, "+3V3", lib)[0] == "U1"  # not on +3V3, but drives it
    assert source_candidates(snap, "+1V8", lib)[0] == "U2"
    vin = source_candidates(snap, "VIN", lib)
    assert vin[0] == "J1" and vin[-1] == "U1"


def test_declared_kinds_and_voltage_fields():
    assert vrm_kind("Switcher") == "smps" and vrm_kind("LDO") == "ldo" and vrm_kind("x") == ""
    lib = PartsLibrary.from_dict({"kipi_si_parts": 1, "parts": {
        "BUCK": {"vrm": {"kind": "smps", "fsw_hz": 1e6}}}})
    assert lib.parts["BUCK"].vrm.kind == "smps"
    with pytest.raises(AutofillError, match="kind"):
        PartsLibrary.from_dict({"kipi_si_parts": 1, "parts": {"X": {"vrm": {"kind": "nope"}}}})
    snap = board(parts={"J1": ("CONN", {"PI_V": "12V"})})
    src = by_ref(find_tree(snap, PartsLibrary()))["J1"]
    assert (src.voltage, src.voltage_from) == (12.0, "PI_V")


def test_noise_phases_and_frequency_from_the_tree():
    snap = board()
    found = find_tree(snap, PartsLibrary())
    by_ref(found)["J1"].voltage = 12.0
    s = autofill_tree(snap, found, PISetup(), PartsLibrary()).setup
    buck = next(v for v in s.vrms if v.output.net == "+3V3")
    assert buck.ground is None                      # the ground net is not simulated
    ph = seed_phases(snap, s, buck, "buck")[0]
    assert (ph.inductor, ph.switch_net) == ("L1", "3V3_SW")
    assert ph.inductance_h == pytest.approx(1e-6)
    assert (ph.high_side.net, ph.low_side.ref, ph.low_side.net) == ("VIN", "U1", "GND")
    assert ph.input_caps == ["C1"] and ph.output_caps == ["C2"]
    assert buck.ground is None                      # the guess is not the VRM's
    assert switching_frequency(snap, buck) == pytest.approx(600e3)


# Four ORed inputs on to VIN_OR, then a P-FET on to VIN: the Jetson carrier's supply.
OR_PARTS = {
    "J9": ("BARREL", {}), "Q5": ("PFET", {}), "Q3": ("PFET", {}), "Q4": ("PFET", {}),
    "Q7": ("MIRROR", {}), "U20": ("POE_MODULE", {}), "U21": ("USB_PD", {}),
    "R20": ("0R", {}), "R21": ("0R", {}), "R22": ("0R", {}),
    "C20": ("10u", {}), "C21": ("10u", {}), "C22": ("10u", {}),
}
OR_PINS = [
    ("J9", "1", "IN_J"), ("J9", "2", "GND"),
    ("Q3", "1", "Net-(Q3-G)"), ("Q3", "2", "VIN_OR"), ("Q3", "3", "IN_J"),
    ("Q4", "1", "Net-(Q4-G)"), ("Q4", "2", "VIN_OR"), ("Q4", "3", "POE"),
    ("Q5", "1", "Net-(Q5-G)"), ("Q5", "2", "VIN_OR"), ("Q5", "3", "VIN"),
    # A current mirror sensing Q3: on two of the path's nets, and no load.
    ("Q7", "1", "VIN_OR"), ("Q7", "2", "Net-(Q7-Pad2)"), ("Q7", "3", "Net-(Q7-Pad2)"),
    ("Q7", "4", "IN_J"), ("Q7", "6", "Net-(Q3-G)"),
    ("U20", "1", "POE"), ("U20", "2", "GND"), ("U20", "3", "POE_CTRL"),
    ("U21", "1", "PD1"), ("U21", "2", "PD2"), ("U21", "3", "GND"), ("U21", "4", "PD_CC"),
    ("C20", "1", "POE"), ("C20", "2", "GND"),
    ("C21", "1", "PD1"), ("C21", "2", "GND"), ("C22", "1", "PD2"), ("C22", "2", "GND"),
    ("R20", "1", "PD1"), ("R20", "2", "VIN_OR"), ("R21", "1", "PD2"), ("R21", "2", "VIN_OR"),
    # Bypass of the switch, not fitted.
    ("R22", "1", "VIN_OR"), ("R22", "2", "VIN"),
]


def ored():
    snap = board(OR_PARTS, OR_PINS, dnp={"R9", "R22"})
    snap.pads = [p for p in snap.pads if p.footprint != "J1"]
    snap.footprints = [f for f in snap.footprints if f.reference != "J1"]
    snap.invalidate_index()
    return snap


def group_rows(found):
    return {f.rail: f for f in found if f.or_group and f.kind == "source"}


def test_ored_inputs_are_offered_not_guessed():
    found = find_tree(ored(), PartsLibrary())
    kinds = {f.ref: f.kind for f in found if f.ref in ("Q3", "Q4", "Q5")}
    assert kinds == {"Q3": "switch", "Q4": "switch", "Q5": "switch"}   # no FET as a source
    src = group_rows(found)
    assert {(r, f.ref) for r, f in src.items()} == {
        ("IN_J", "J9"), ("POE", "U20"), ("PD1", "U21"), ("PD2", "U21")}
    assert not any(f.use for f in src.values())         # the user's to pick
    assert {f.or_group for f in src.values()} == {"VIN_OR"}
    assert src["IN_J"].branch == ["Q3"] and src["PD1"].branch == ["R20"]


def pick(found, rail, volts):
    f = group_rows(found)[rail]
    f.use, f.voltage = True, volts
    return found


def test_ored_inputs_need_exactly_one_picked():
    snap = ored()
    found = find_tree(snap, PartsLibrary())
    with pytest.raises(AutofillError, match="pick one input"):
        autofill_tree(snap, found, PISetup(), PartsLibrary())
    pick(pick(found, "IN_J", 12.0), "POE", 12.0)
    with pytest.raises(AutofillError, match="pick one input"):
        autofill_tree(snap, found, PISetup(), PartsLibrary())


def test_only_the_picked_input_is_in_the_tree():
    snap = ored()
    found = pick(find_tree(snap, PartsLibrary()), "IN_J", 12.0)
    s = autofill_tree(snap, found, PISetup(), PartsLibrary()).setup
    assert [v.output.ref for v in s.vrms if v.kind == "source"] == ["J9"]
    assert {k.side_a.ref for k in s.links} >= {"Q3", "Q5"}
    assert not {"Q4", "R20", "R21"} & {k.side_a.ref for k in s.links}
    assert not {"Q7", "U20", "U21"} & {l.supply.ref for l in s.loads}
    assert not {"POE", "PD1", "PD2"} & set(s.nets)
    assert validate(s) == []


def test_changing_the_pick_replaces_the_source_and_is_remembered():
    snap = ored()
    lib = PartsLibrary()
    first = autofill_tree(snap, pick(find_tree(snap, lib), "IN_J", 12.0), PISetup(), lib).setup
    again = group_rows(find_tree(snap, lib, first))
    assert again["IN_J"].use and again["IN_J"].voltage == 12.0
    assert not again["POE"].use
    second = autofill_tree(snap, pick(find_tree(snap, lib), "POE", 48.0), first, lib).setup
    assert [(v.output.ref, v.voltage) for v in second.vrms if v.kind == "source"] == [("U20", 48.0)]
    assert "IN_J" not in second.nets and "Q3" not in {k.side_a.ref for k in second.links}


def test_one_input_behind_a_switch_is_the_source():
    snap = board({"J9": ("BARREL", {}), "Q5": ("PFET", {})},
                 [("J9", "1", "RAW"), ("J9", "2", "GND"),
                  ("Q5", "1", "Net-(Q5-G)"), ("Q5", "2", "RAW"), ("Q5", "3", "VIN")])
    snap.pads = [p for p in snap.pads if p.footprint != "J1"]
    snap.footprints = [f for f in snap.footprints if f.reference != "J1"]
    snap.invalidate_index()
    f = by_ref(find_tree(snap, PartsLibrary()))
    assert (f["J9"].kind, f["J9"].rail, f["J9"].use, f["J9"].or_group) == ("source", "RAW", True, "")
    assert f["Q5"].kind == "switch" and f["Q5"].use


def test_dialog_makes_the_user_pick_one_input():
    from qtpy.QtCore import Qt
    from qtpy.QtWidgets import QApplication, QDialogButtonBox
    from kipi_si.dc.gui.tree_autofill_dialog import TreeAutofillDialog
    _app = QApplication.instance() or QApplication([])
    snap = ored()
    d = TreeAutofillDialog(snap, PartsLibrary(), find_tree(snap, PartsLibrary()))
    ok = d.buttons.button(QDialogButtonBox.Ok)
    row = {(f.ref, f.rail): i for i, f in enumerate(d.rows)}
    use = lambda key: d.table.item(row[key], 0)
    q3, q4 = next(k for k in row if k[0] == "Q3"), next(k for k in row if k[0] == "Q4")
    assert not ok.isEnabled() and "Pick the input to VIN_OR" in d.status.text()
    use(("J9", "IN_J")).setCheckState(Qt.Checked)
    assert use(q3).checkState() == Qt.Checked and use(q4).checkState() == Qt.Unchecked
    use(("U20", "POE")).setCheckState(Qt.Checked)       # one at a time
    assert use(("J9", "IN_J")).checkState() == Qt.Unchecked
    assert use(q3).checkState() == Qt.Unchecked and use(q4).checkState() == Qt.Checked
    assert not ok.isEnabled() and "U20 a voltage" in d.status.text()
