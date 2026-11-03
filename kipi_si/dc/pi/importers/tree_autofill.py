"""Fill the whole power tree from the board: find every regulator, the source each input
rail comes in from, and walk each one's rail as Auto-fill rail does.

:func:`find_tree` reads the board and returns what it found, for the user to check and
change in a preview; :func:`autofill_tree` then fills the setup from those rows.

How a regulator is recognised, first found wins:

1. its ``PI_VRM`` field ('switcher', 'ldo' or 'source') or the library's ``vrm: {kind}``;
2. a **switcher**: an inductor between a switch node and a rail. The switch node is a
   net with an IC (or a FET) on it and no capacitor to ground; the rail has one. The IC
   is the switching device. The output is the rail its feedback divider comes from, so
   an inductor on the input with the divider on the far rail is a boost; without a
   divider it is a buck, the inductor on its output. Inductors from one rail to several
   switch nodes are the phases of one VRM;
3. an **LDO**: an IC on exactly two rails (nets with a capacitor to ground and something
   else on them), with no more than one signal to another part (a power-good). A part with
   more (a level translator, a buffer) is a load on both. The output is the lower rail by
   the names' voltages, else the one the IC is the only active part on. Two rails at the
   same voltage are a load switch, not a regulator.

Each regulator's input rail (and the nets joined to it by series parts) that no regulator
drives is fed by a **switch** when a transistor joins it to a rail that is fed (a P-FET
load switch: a DC connection through the transistor), else gets a **source**: on the rail's
connector, else the transistor or diode the power comes in through, else another part on
it, marked for checking.

Voltages: the part's ``PI_V`` field, the library, the rail's name; else left for the user.
"""

from __future__ import annotations

import copy
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from kipi_si.core.model.board import BoardSnapshot, Footprint
from kipi_si.core.model.nets import voltage_from_name
from kipi_si.core.model.parts import is_capacitor_ref, is_inductor_ref
from kipi_si.dc.pi.autofill import (
    guess_ground_pins, input_net, is_passive_ref, looks_like_ground, net_kinds, part_nets,
    refs_on_net,
)
from kipi_si.dc.pi.importers.rail_autofill import (
    DEFAULT_MAX_LINK_OHM, AutofillResult, PartEntry, PartsLibrary, _merge, _ref_key, _Walker,
    library_paths, parse_quantity, part_voltage, vrm_kind,
)
from kipi_si.dc.pi.model import PinRef, PISetup, Vrm, VrmPhase

_IC_RE = re.compile(r"^(U|IC|VR|PS|PM|N)\d", re.IGNORECASE)
_FET_RE = re.compile(r"^(Q|M|T)\d", re.IGNORECASE)
_CONN_RE = re.compile(r"^(J|P|CN|X|CON)\d", re.IGNORECASE)
_DIODE_RE = re.compile(r"^D\d", re.IGNORECASE)
_FB_RE = re.compile(r"(^|[^A-Z])V?FB|FEEDBACK|VSENSE", re.IGNORECASE)
KINDS = ("source", "ldo", "smps", "switch")
KIND_NAMES = {"source": "Source", "ldo": "LDO", "smps": "Switcher", "switch": "Switch"}


@dataclass
class Found:
    """One row of the preview: a VRM to add, as found on the board."""
    ref: str                            # the regulator's (or source's, or switch's) part
    kind: str                           # "source", "ldo", "smps" or "switch"
    output: PinRef                      # phase 1's pins on the rail (a switch's far side)
    input: Optional[PinRef] = None
    ground: Optional[PinRef] = None     # the part's ground pins, when it has them
    phases: List[VrmPhase] = field(default_factory=list)    # phases 2..N
    voltage: Optional[float] = None
    voltage_from: str = ""              # "PI_V", "library", "net name" or "" (unknown)
    inductors: List[str] = field(default_factory=list)
    switch_nets: List[str] = field(default_factory=list)
    why: str = ""                       # how it was recognised
    check: str = ""                     # what the user should check; "" when sure
    use: bool = True
    current_limit_a: Optional[float] = None
    fsw_hz: Optional[float] = None      # PI_FSW or the library, for Coupled Noise

    @property
    def rail(self) -> str:
        return self.output.net

    def refs(self) -> Set[str]:
        """Every part of this VRM: its devices and output parts, in every phase."""
        out = set()
        for ph in [VrmPhase(self.output, self.input, self.ground), *self.phases]:
            out |= {r.ref for r in (ph.output, ph.input, ph.ground) if r is not None}
        return out

    def feeds(self) -> Set[Tuple[str, str]]:
        """(part, net) of its input pins in every phase."""
        return {(ph.input.ref, ph.input.net)
                for ph in [VrmPhase(self.output, self.input, self.ground), *self.phases]
                if ph.input is not None}


class _Board:
    """The board's parts and nets, indexed for the searches below."""

    def __init__(self, snap: BoardSnapshot, library: PartsLibrary):
        self.snap, self.lib = snap, library
        # Parts not fitted (KiCad's DNP) are not on the board for this.
        self.fps: Dict[str, Footprint] = {f.reference: f for f in snap.footprints if not f.dnp}
        self.kinds = net_kinds(snap)
        self._caps: Dict[str, bool] = {}

    def nets(self, ref: str) -> Dict[str, List[str]]:
        return part_nets(self.snap, ref)

    def on(self, net: str) -> List[str]:
        return [r for r in refs_on_net(self.snap, net) if r in self.fps]

    def ground(self, net: str) -> bool:
        return looks_like_ground(self.snap, net)

    def entry(self, ref: str) -> Optional[PartEntry]:
        fp = self.fps.get(ref)
        return self.lib.lookup(fp) if fp else None

    def field(self, ref: str, name: str) -> str:
        fp = self.fps.get(ref)
        return (fp.fields.get(name) or "").strip() if fp else ""

    def role(self, ref: str) -> str:
        e = self.entry(ref)
        return (self.field(ref, "PI_ROLE") or (e.role if e else "")).lower()

    def declared(self, ref: str) -> str:
        """The VRM type its PI_VRM field or library entry gives, or ''."""
        k = vrm_kind(self.field(ref, "PI_VRM"))
        if not k:
            e = self.entry(ref)
            k = e.vrm.kind if e and e.vrm else ""
        return k

    def cap_to_ground(self, net: str) -> bool:
        """Whether a capacitor joins ``net`` to a ground."""
        if net not in self._caps:
            self._caps[net] = any(
                is_capacitor_ref(r) and len(ns := self.nets(r)) == 2
                and any(self.ground(n) for n in ns if n != net)
                for r in self.on(net))
        return self._caps[net]

    def active(self, net: str, but: str = "") -> List[str]:
        """The parts on ``net`` that are not passive, but ``but``."""
        return [r for r in self.on(net) if r != but and not is_passive_ref(r)]

    def series_out(self, ref: str, net: str) -> bool:
        """Whether ``ref`` is a two-terminal series part out of ``net`` (a resistor of 1 Ω
        or less, a bead, a fuse) to a net that is not a ground."""
        ns = self.nets(ref)
        if len(ns) != 2 or net not in ns or is_capacitor_ref(ref):
            return False
        far = next(n for n in ns if n != net)
        if self.ground(far):
            return False
        if ref[:1].upper() == "R":
            from kipi_si.core.model.parts import parse_resistance, part_value
            r = parse_resistance(part_value(self.fps[ref], parse_resistance)) \
                if ref in self.fps else None
            return r is not None and r <= DEFAULT_MAX_LINK_OHM
        return bool(re.match(r"^(FB|FL|BEAD|F|L)\d", ref, re.IGNORECASE))

    def is_rail(self, net: str, ref: str) -> bool:
        """Whether ``net``, one of part ``ref``'s, is a rail: not a ground, a capacitor to
        ground on it, and something besides ``ref`` and capacitors: an active part, or a
        series part on to another net."""
        if self.ground(net) or not self.cap_to_ground(net):
            return False
        return bool(self.active(net, ref)) or any(
            self.series_out(r, net) for r in self.on(net) if r != ref)

    def signals(self, ref: str, rails: List[str]) -> List[str]:
        """Part ``ref``'s nets that reach another active part and are neither a ground nor
        one of ``rails``: its signals."""
        return [n for n in self.nets(ref)
                if n not in rails and not self.ground(n) and self.active(n, ref)]

    def divider_rail(self, ref: str, rail: str, exclude=()) -> Optional[str]:
        """The rail a feedback divider into part ``ref`` comes from: a resistor from one
        of its nets only passives are on to a net with a capacitor to ground. A net named
        like feedback (FB) wins, then a divider (with a resistor to ground on the node too:
        not an enable pull-up), then ``rail`` itself among the rest."""
        hits = []                       # (named FB, has a leg to ground, far rail)
        for n in self.nets(ref):
            if n in exclude or self.ground(n) or self.active(n, ref):
                continue
            legs = [self.nets(r) for r in self.on(n)
                    if r[:1].upper() == "R" and len(self.nets(r)) == 2]
            to_ground = any(self.ground(x) for ns in legs for x in ns if x != n)
            for ns in legs:
                far = next(x for x in ns if x != n)
                if far not in exclude and not self.ground(far) and self.cap_to_ground(far):
                    hits.append((bool(_FB_RE.search(n)), to_ground, far))
        for test in (lambda h: h[0], lambda h: h[1]):
            fars = list(dict.fromkeys(h[2] for h in hits if test(h)))
            if fars:
                return rail if rail in fars else fars[0]
        return rail if any(h[2] == rail for h in hits) else None

    def pick_device(self, refs: List[str], net: str) -> Optional[str]:
        """The IC (else the transistor) of ``refs`` with the most pins on ``net``."""
        for pat in (_IC_RE, _FET_RE):
            cands = [r for r in refs if pat.match(r)]
            if cands:
                return max(cands, key=lambda r: (len(self.nets(r).get(net, [])), -_ref_key_n(r)))
        return None


def _ref_key_n(ref: str) -> int:
    m = re.search(r"(\d+)$", ref)
    return int(m.group(1)) if m else 0


def _volts(net: str) -> Optional[float]:
    return voltage_from_name(net)


# ---------------------------------------------------------------------------
# Switchers
# ---------------------------------------------------------------------------

def _switchers(b: _Board) -> List[Found]:
    """Every switcher, from the inductors between a switch node and a rail."""
    hits = []                           # (device, inductor, switch net, rail)
    for ref in sorted(b.fps, key=_ref_key):
        if not is_inductor_ref(ref) or b.role(ref) in ("ignore", "load"):
            continue
        ns = list(b.nets(ref))
        if len(ns) != 2 or any(b.ground(n) for n in ns):
            continue
        for sw, rail in ((ns[0], ns[1]), (ns[1], ns[0])):
            devs = b.active(sw, ref)
            if not devs or b.cap_to_ground(sw) or not b.cap_to_ground(rail):
                continue
            dev = b.pick_device(devs, sw)
            if dev:
                hits.append((dev, ref, sw, rail))
                break
    # Each inductor's topology first: a boost's inductor ends on its input, which may be
    # a buck's output. Then one VRM per output rail and topology: its inductors are phases.
    groups: Dict[Tuple[str, str], list] = {}
    notes: Dict[Tuple[str, str], List[str]] = {}
    for dev, ind, sw, rail in hits:
        fb = b.divider_rail(dev, rail, exclude=[sw])
        boost_out, note = (fb if fb and fb != rail else None), []
        if boost_out and not b.nets(dev).get(boost_out):
            note.append(f"its feedback is from {boost_out}, but it has no pins there: "
                        "taken as a buck")
            boost_out = None
        if not fb and not b.nets(dev).get(rail):
            note.append("no feedback divider found: taken as a buck")
        key = (boost_out or rail, "boost" if boost_out else "buck")
        groups.setdefault(key, []).append((dev, ind, sw, rail))
        notes.setdefault(key, [])
        notes[key] += [n for n in note if n not in notes[key]]
    out = []
    for (out_net, topo), group in groups.items():
        devices = list(dict.fromkeys(h[0] for h in group))
        sw_nets = [h[2] for h in group]
        phases = []
        for dev, ind, sw, rail in group:
            gnd = guess_ground_pins(b.snap, None, None, PinRef(dev, sw))
            if topo == "boost":
                # Drawn from the rail through the inductor, out of the device.
                phases.append(VrmPhase(PinRef(dev, out_net, list(b.nets(dev)[out_net])),
                                       PinRef(ind, rail, list(b.nets(ind)[rail])), gnd))
            else:
                exclude = [rail, sw] + ([gnd.net] if gnd else [])
                vin = input_net(b.snap, dev, exclude)
                phases.append(VrmPhase(PinRef(ind, rail, list(b.nets(ind)[rail])),
                                       PinRef(dev, vin, list(b.nets(dev)[vin])) if vin else None,
                                       gnd))
        f = Found(devices[0], "smps", phases[0].output, phases[0].input, phases[0].ground,
                  phases[1:], inductors=[h[1] for h in group], switch_nets=sw_nets)
        f.why = (f"switcher ({topo}): {', '.join(f.inductors)} from switch node "
                 f"{', '.join(sw_nets)} to {', '.join(dict.fromkeys(h[3] for h in group))}")
        if len(group) > 1:
            f.why += f", {len(group)} phases"
        checks = list(notes[(out_net, topo)])
        if any(ph.input is None for ph in phases):
            checks.append("input rail not found: pick its input pins")
        f.check = "; ".join(checks)
        _voltage(b, f, out_net)
        out.append(f)
    return out


# ---------------------------------------------------------------------------
# LDOs
# ---------------------------------------------------------------------------

def _ldos(b: _Board, skip: Set[str]) -> List[Found]:
    out = []
    for ref in sorted(b.fps, key=_ref_key):
        if ref in skip or not _IC_RE.match(ref) or b.role(ref) in ("ignore", "load", "link"):
            continue
        nets = b.nets(ref)
        rails = [n for n in nets if b.is_rail(n, ref)]
        if len(rails) != 2:
            continue
        sig = b.signals(ref, rails)
        if len(sig) > 1:
            continue                    # a translator or buffer on two supplies: a load
        grounds = [n for n in nets if b.ground(n)]
        if len(set(grounds)) > 1:
            continue                    # an isolated converter: set by hand
        va, vb = _volts(rails[0]), _volts(rails[1])
        check = ""
        if va is not None and vb is not None:
            if abs(va - vb) < 1e-6:
                continue                # a load switch: not a regulator
            vin, vout = (rails[0], rails[1]) if va > vb else (rails[1], rails[0])
            why = "by the rails' voltages"
        else:
            only = [n for n in rails if not b.active(n, ref)]
            if len(only) != 1:
                continue                # can't tell which way it regulates
            vout = only[0]
            vin = next(n for n in rails if n != vout)
            why = f"the only active part on {vout}"
            if vb is None and va is None:
                check = "which side is its output is a guess: check it"
        gnd = guess_ground_pins(b.snap, None, None, PinRef(ref, vout))
        f = Found(ref, "ldo", PinRef(ref, vout, list(nets[vout])),
                  PinRef(ref, vin, list(nets[vin])), gnd,
                  why=f"LDO: from {vin} to {vout} ({why})", check=check)
        _voltage(b, f, vout)
        out.append(f)
    return out


def _declared(b: _Board, skip: Set[str]) -> List[Found]:
    """Parts their PI_VRM field or the library call a regulator, not found above."""
    out = []
    for ref in sorted(b.fps, key=_ref_key):
        kind = b.declared(ref)
        if ref in skip or kind not in ("ldo", "smps"):
            continue
        nets = b.nets(ref)
        rails = [n for n in nets if not b.ground(n) and b.kinds.get(n) == "power"]
        e = b.entry(ref)
        pins = e.vrm.out_pins if e and e.vrm else []
        vout = next((n for n in rails if pins and set(pins) <= set(nets[n])), None)
        if vout is None:
            continue
        vin = input_net(b.snap, ref, [vout])
        gnd = guess_ground_pins(b.snap, None, None, PinRef(ref, vout))
        f = Found(ref, kind, PinRef(ref, vout, list(pins)),
                  PinRef(ref, vin, list(nets[vin])) if vin else None, gnd,
                  why=f"{KIND_NAMES[kind]}: by its PI_VRM field or the library",
                  check="" if vin else "input rail not found: pick its input pins")
        _voltage(b, f, vout)
        out.append(f)
    return out


def _voltage(b: _Board, f: Found, net: str):
    fp = b.fps.get(f.ref)
    e = b.entry(f.ref)
    if fp is not None:
        f.voltage, f.voltage_from = part_voltage(fp, e, net)
    else:
        v = voltage_from_name(net)
        f.voltage, f.voltage_from = v, "net name" if v is not None else ""
    f.current_limit_a = parse_quantity(b.field(f.ref, "PI_IMAX"), "A")
    if f.current_limit_a is None and e and e.vrm:
        f.current_limit_a = e.vrm.current_limit_a
    f.fsw_hz = parse_quantity(b.field(f.ref, "PI_FSW"), "Hz")
    if f.fsw_hz is None and e and e.vrm:
        f.fsw_hz = e.vrm.fsw_hz


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

def rail_group(b: _Board, net: str, stop: Set[str]) -> List[str]:
    """``net`` and the nets its series parts join it to, short of the nets in ``stop``."""
    seen, todo = [net], deque([net])
    while todo:
        n = todo.popleft()
        for r in b.on(n):
            if b.series_out(r, n):
                far = next(x for x in b.nets(r) if x != n)
                if far not in seen and far not in stop:
                    seen.append(far)
                    todo.append(far)
    return seen


def _sources(b: _Board, regs: List[Found]) -> List[Found]:
    """A source for each regulator input rail no regulator drives."""
    outs = {f.rail for f in regs}
    switch_nets = {n for f in regs for n in f.switch_nets}
    devices = {r for f in regs for r in f.refs()}
    covered: Set[str] = set()
    for f in regs:
        covered |= set(rail_group(b, f.rail, (outs - {f.rail}) | switch_nets))
    out = []
    inputs = list(dict.fromkeys(ph.input.net for f in regs
                                for ph in [VrmPhase(f.output, f.input, f.ground), *f.phases]
                                if ph.input is not None))
    for net in inputs:
        if net in covered:
            continue
        group = rail_group(b, net, outs | switch_nets)
        sw = _switch_into(b, net, covered, devices)
        covered |= set(group)
        if sw is not None:
            out.append(sw)
            continue
        ref, how = _entry_part(b, net, devices)
        if ref is None:
            continue
        pins = b.nets(ref).get(net, [])
        f = Found(ref, "source", PinRef(ref, net, list(pins)),
                  ground=guess_ground_pins(b.snap, None, None, PinRef(ref, net)),
                  why=f"source: {net} feeds {_fed(regs, group)} and no regulator drives it; "
                      f"{how}",
                  check="" if how.startswith("its connector") else
                  "where the power comes in is a guess: check the part")
        _voltage(b, f, net)
        out.append(f)
    return out


def _switch_into(b: _Board, net: str, covered: Set[str], devices: Set[str]
                 ) -> Optional[Found]:
    """A transistor joining ``net`` to a rail in ``covered`` (a load switch), as a switch
    row, or None. Its third net is its gate."""
    for r in b.on(net):
        if r in devices or not _FET_RE.match(r) or b.role(r) == "ignore":
            continue
        ns = b.nets(r)
        if len(ns) != 3:
            continue
        up = [n for n in ns if n != net and n in covered and not b.ground(n)]
        if len(up) != 1:
            continue
        return Found(r, "switch", PinRef(r, net, list(ns[net])),
                     PinRef(r, up[0], list(ns[up[0]])),
                     why=f"switch: {r} joins {up[0]} to {net}, as a DC connection",
                     check="" if b.field(r, "PI_R") else
                     "its on-resistance is not known (PI_R): taken as a short")
    return None


def _fed(regs: List[Found], group: List[str]) -> str:
    names = [f.ref for f in regs if f.input is not None and f.input.net in group]
    return ", ".join(names) or "regulators"


def _entry_part(b: _Board, net: str, devices: Set[str]) -> Tuple[Optional[str], str]:
    """The part the power comes into ``net`` through, and how it was chosen."""
    cands = [r for r in b.on(net) if r not in devices and not is_capacitor_ref(r)
             and not re.match(r"^(R|L|FB|FL|TP)\d", r, re.IGNORECASE)
             and b.role(r) != "ignore"]
    declared = [r for r in cands if b.declared(r) == "source"]
    if declared:
        return declared[0], "its PI_VRM field says source"
    conns = [r for r in cands if _CONN_RE.match(r)]
    if conns:
        return conns[0], "its connector"

    def path(r: str) -> bool:
        """In the power's path: on another net that is not a ground (not a TVS diode)."""
        return any(n != net and not b.ground(n) for n in b.nets(r))

    for pat, what in ((_FET_RE, "transistor"), (_DIODE_RE, "diode")):
        hits = [r for r in cands if pat.match(r) and path(r)]
        if hits:
            return hits[0], f"the {what} on it, where the power likely comes in"
    others = [r for r in cands if not _DIODE_RE.match(r)]
    if others:
        return others[0], "a part on it, for want of a connector"
    return None, ""


# ---------------------------------------------------------------------------
# The whole tree
# ---------------------------------------------------------------------------

def find_tree(snap: BoardSnapshot, library: Optional[PartsLibrary] = None) -> List[Found]:
    """Every regulator on the board, then a source for each input rail none drives: the
    sources first, then the regulators by their rails' order down the tree."""
    if library is None:
        library = PartsLibrary.load(library_paths(snap.project_dir))
    b = _Board(snap, library)
    regs = _switchers(b)
    taken = {r for f in regs for r in f.refs()} | {i for f in regs for i in f.inductors}
    regs += _ldos(b, taken)
    taken |= {r for f in regs for r in f.refs()}
    regs += _declared(b, taken)
    # A part the user calls a source is a source, wherever it sits.
    srcs = _sources(b, regs)
    return srcs + _tree_order(regs)


def _tree_order(regs: List[Found]) -> List[Found]:
    """Regulators fed from the sources first, then those fed from them, and so on."""
    outs = {f.rail: f for f in regs}
    depth: Dict[int, int] = {}

    def d(f: Found, seen=()) -> int:
        if id(f) in depth:
            return depth[id(f)]
        up = outs.get(f.input.net) if f.input is not None else None
        depth[id(f)] = 0 if up is None or up in seen else d(up, (*seen, f)) + 1
        return depth[id(f)]

    return sorted(regs, key=lambda f: (d(f), _ref_key(f.ref)))


def to_vrm(f: Found, name: str, include_ground: bool) -> Vrm:
    v = Vrm(name=name, output=copy.deepcopy(f.output), voltage=f.voltage or 1.0,
            kind=f.kind, input=copy.deepcopy(f.input) if f.kind != "source" else None,
            ground=copy.deepcopy(f.ground) if include_ground else None,
            current_limit_a=f.current_limit_a)
    if f.kind != "source":
        v.phases = [VrmPhase(copy.deepcopy(p.output), copy.deepcopy(p.input),
                             copy.deepcopy(p.ground) if include_ground else None)
                    for p in f.phases]
    return v


def autofill_tree(snap: BoardSnapshot, found: List[Found], base: Optional[PISetup] = None,
                  library: Optional[PartsLibrary] = None, include_ground: bool = False,
                  max_link_ohm: float = DEFAULT_MAX_LINK_OHM) -> AutofillResult:
    """``base`` with each row of ``found`` that is in use as a VRM and its rail's loads,
    series parts and capacitors, walked as :func:`~.rail_autofill.autofill_rail` walks
    one rail. A part that is a VRM's input is not a load on the rail feeding it."""
    if library is None:
        library = PartsLibrary.load(library_paths(snap.project_dir))
    rows = [f for f in found if f.use and f.kind != "switch"]
    switches = {f.ref: (f.input.net, f.rail) for f in found
                if f.use and f.kind == "switch" and f.input is not None}
    outs = {f.rail for f in rows}
    feeds = {x for f in rows for x in f.feeds()}
    inductors = {i for f in rows for i in f.inductors}
    switch_nets = {n for f in rows for n in f.switch_nets}
    setup = copy.deepcopy(base) if base is not None else PISetup()
    notes: List[str] = []
    nets: List[str] = []
    missing: Dict[str, object] = {}
    names = {x.name for x in [*setup.vrms]}
    for f in rows:
        fp = next((x for x in snap.footprints if x.reference == f.ref), None)
        base_name = f"{f.ref} {fp.value}".strip() if fp is not None and fp.value else f.ref
        name, n = base_name, 2
        while name in names and not any(v.name == name and v.output.net == f.rail
                                        for v in setup.vrms):
            name, n = f"{base_name} ({n})", n + 1
        names.add(name)
        if f.voltage is None:
            notes.append(f"{name}: voltage not known, set to 1 V; set it on the VRMs tab")
        vrm = to_vrm(f, name, include_ground)
        w = _Walker(snap, f.rail, f.output.ref, library, include_ground, max_link_ohm,
                    vrm=vrm, taken=f.refs() | inductors, feeds=feeds,
                    stop=(outs - {f.rail}) | switch_nets, switches=switches)
        rail_nets = w.run()
        setup = _merge(setup, w, rail_nets)
        notes += w.notes
        nets += [x for x in rail_nets if x not in nets]
        for m in w.missing.values():
            have = missing.setdefault(m.key, m)
            if have is not m:
                have.refs += [r for r in m.refs if r not in have.refs]
    return AutofillResult(setup, notes, nets, list(missing.values()))


def regulator_for(snap: BoardSnapshot, rail: str, ref: str,
                  library: Optional[PartsLibrary] = None) -> Optional[Found]:
    """The regulator :func:`find_tree` finds on part ``ref`` driving ``rail`` (or ``ref``
    as one of its inductors), or None: what Auto-fill rail makes of a source it picks."""
    for f in find_tree(snap, library):
        if f.kind != "source" and f.rail == rail and (ref in f.refs() or ref in f.inductors):
            return f
    return None
