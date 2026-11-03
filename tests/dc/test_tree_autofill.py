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
