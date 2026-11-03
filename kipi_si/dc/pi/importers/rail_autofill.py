"""Fill one rail's power tree from the board: its source, every part in series into its
branches, and every load, with currents and ratings from a parts library and the parts'
own fields.

Pick a rail and the part that drives it. The walk starts at the rail's net and visits
every footprint with pads on it:

* the source part -> a ``source`` VRM on its pads on the rail;
* a two-pad part to another net that is not a ground and passes DC (a ferrite, an
  inductor, a resistor at or below ``max_link_ohm``, or a part the library or its fields
  call a link) -> a DC connection, and the walk goes on into the net beyond it;
* a capacitor from the net to a ground -> an AC capacitor model, one per value and
  package (see "Capacitors" below), unless a model has it already;
* test points, higher-value resistors (pull-ups, dividers) and parts not fitted (KiCad's
  DNP, unless a ``PI_ROLE`` says otherwise) -> skipped;
* anything else -> a load on its pads on the net.

Where the numbers come from, the first found wins:

1. the part's fields, set in the schematic and copied to the board (``PI_I``, ``PI_R``,
   ``PI_IMAX``, ``PI_PMAX``, ``PI_TOL``, ``PI_ROLE``; see :data:`FIELDS`);
2. the parts library, ``pi_parts.yml`` beside the board and then in the user's KiPI-SI
   folder, keyed by manufacturer part number (or value);
3. a resistor's value field, for its resistance.

Nothing is guessed: a load with no current is added at 0 A, a series part with no
resistance as a short, and both are named in the notes, to be filled in.

Capacitors: the capacitance is the value field's (or the library's). The ESL is the
``PI_ESL`` field's, else the library's, else the part's own from its package
(:func:`~kipi_si.core.model.parts.part_esl`; the solve adds the board's mounting). The ESR is
the ``PI_ESR`` field's, else the library's, else, for a ceramic chip, a typical MLCC's at
its capacitance (:func:`~kipi_si.core.model.parts.mlcc_esr_ohm`), named an estimate in the
notes. Anything still unknown is left 0 ("values needed") and named in the notes.

Library file:

.. code-block:: yaml

    kipi_si_parts: 1
    parts:
      LMH6518SQX/NOPB:                  # MPN, or the value field
        supplies:                       # as in a load model (kipi_si.dc.pi.load_model)
          - {name: VA, pins: ['3', '4'], current_a: 0.23,
             tolerance: {min: -5, max: 5, unit: "%"}}
      BLM15PX121SN1D:
        link: {resistance_ohm: 0.055, current_max_a: 2.0}
      RC0402FR-070R1L:
        link: {power_max_w: 0.0625}     # its resistance from its value field
      TPS7A9101DSKR:
        vrm: {out_pins: ['1', '2'], current_limit_a: 1.0}
      SIC431AED-T1-GE3:
        vrm: {kind: smps, fsw_hz: 600e3}  # smps, ldo or source, for Auto-fill power tree
      GRM155R71C104KA88D:
        cap: {capacitance_f: 100e-9, esl_h: 0.4e-9, esr_ohm: 0.03}
      TP-5000:
        role: ignore                    # load, link, vrm or ignore
"""

from __future__ import annotations

import copy
import math
import os
import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

from kipi_si.core.model.board import BoardSnapshot, Footprint
from kipi_si.core.model.nets import voltage_from_name
from kipi_si.ac.model import AGING_PCT_PER_DECADE, CapModel
from kipi_si.core.model.parts import (
    chip_length_mm, is_capacitor_ref, is_class2, is_inductor_ref, is_mlcc, mlcc_esr_ohm,
    parse_capacitance, parse_dielectric, parse_resistance, parse_voltage_rating, part_esl,
    part_value,
)
from kipi_si.dc.pi.autofill import guess_ground_pins, looks_like_ground, part_nets, pins_on
from kipi_si.dc.pi.load_model import (
    LoadModel, ModelError, SupplyModel, _supply, apply_to_load, best_supply,
)
from kipi_si.dc.pi.model import DELTA_VOLTS, PERCENT, DcLink, Load, PinGroup, PinRef, PISetup, Vrm

LIB_KEY = "kipi_si_parts"
LIB_FORMAT = 1
LIB_NAME = "pi_parts.yml"
# Fields that hold a part's manufacturer part number, the library's key, first found wins.
MPN_FIELDS = ("MANUFACTURER PART NUMBER", "MPN", "Manufacturer_Part_Number",
              "Manufacturer Part Number", "MFR PART NUMBER", "MFN", "PN")
FIELDS = {
    "PI_I": "load current: '230mA', or by pins '3,4=230mA; 12=0.4mA'",
    "PI_R": "series part's DC resistance: '55m', '0.1'",
    "PI_IMAX": "current rating: a series part's, or a source's limit: '2A'",
    "PI_PMAX": "power rating of a series part: '63mW'",
    "PI_TOL": "supply tolerance: '±5%', '-3/+5%', '±0.1V'",
    "PI_ROLE": "load, link, vrm or ignore",
    "PI_VRM": "a regulator's type, for Auto-fill power tree: 'switcher', 'ldo' or 'source'",
    "PI_V": "a source's or regulator's output voltage: '12V'",
    "PI_FSW": "a switcher's switching frequency, for Coupled Noise: '600kHz'",
    "PI_ESL": "capacitor's ESL: '0.4nH'",
    "PI_ESR": "capacitor's ESR: '30m'",
}
ROLES = ("load", "link", "vrm", "ignore")
DEFAULT_MAX_LINK_OHM = 1.0
_TP_REF_RE = re.compile(r"^TP\d")
_BEAD_REF_RE = re.compile(r"^(FB|FL|BEAD)\d", re.IGNORECASE)


class AutofillError(ValueError):
    """A rail or source the board does not have, or a parts library KiPI-SI cannot read."""


# ---------------------------------------------------------------------------
# Values in fields: "230mA", "55m", "2A", "63mW", "±5%"
# ---------------------------------------------------------------------------

_SI = {"": 1.0, "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "μ": 1e-6, "m": 1e-3,
       "k": 1e3, "K": 1e3, "M": 1e6}
_QTY_RE = re.compile(r"^\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*([pnuµμmkKM]?)\s*([A-Za-zΩ]*)\s*$")


def parse_quantity(text: str, unit: str) -> Optional[float]:
    """A number with an optional SI prefix and ``unit`` ("230mA", "0.23", "63 mW"), or
    None if ``text`` is not one."""
    m = _QTY_RE.match(text or "")
    if not m:
        return None
    num, prefix, u = m.groups()
    if u and u.lower() != unit.lower():
        if not prefix and u[0] in _SI and u[1:].lower() == unit.lower():
            prefix, u = u[0], u[1:]         # "mA" read as one word
        else:
            return None
    return float(num) * _SI[prefix]


def parse_ohms(text: str) -> Optional[float]:
    return parse_quantity(text, "Ω") if "Ω" in (text or "") else (
        parse_quantity(text, "ohm") if "ohm" in (text or "").lower() else parse_resistance(text))


def parse_pin_currents(text: str) -> Tuple[Optional[float], List[PinGroup]]:
    """``PI_I``: a total current ("230mA"), or currents by pins ("3,4=230mA; 12=0.4mA")
    as pin groups. (None, []) if it can't be read."""
    text = (text or "").strip()
    if "=" not in text:
        return parse_quantity(text, "A"), []
    groups = []
    for part in re.split(r"[;|]", text):
        if not part.strip():
            continue
        pins, sep, amps = part.partition("=")
        a = parse_quantity(amps, "A")
        names = [p.strip() for p in re.split(r"[,\s]+", pins) if p.strip()]
        if not sep or a is None or not names:
            return None, []
        groups.append(PinGroup(names, a))
    return None, groups


_TOL_RE = re.compile(r"^\s*(?:(±|\+/-)\s*(\d*\.?\d+)|([-+]?\d*\.?\d+)\s*/\s*([-+]?\d*\.?\d+))"
                     r"\s*(%|mV|V)\s*$")


def parse_tolerance(text: str) -> Optional[Tuple[float, float, str]]:
    """``PI_TOL``: (min, max, unit) from "±5%", "-3/+5%" or "±100mV", or None."""
    m = _TOL_RE.match(text or "")
    if not m:
        return None
    sym, both, lo, hi, unit = m.groups()
    lo, hi = (-float(both), float(both)) if sym else (float(lo), float(hi))
    if unit == "mV":
        lo, hi, unit = lo / 1e3, hi / 1e3, "V"
    return lo, hi, PERCENT if unit == "%" else DELTA_VOLTS


# ---------------------------------------------------------------------------
# The parts library
# ---------------------------------------------------------------------------

@dataclass
class PartLink:
    resistance_ohm: Optional[float] = None
    current_max_a: Optional[float] = None
    power_max_w: Optional[float] = None


@dataclass
class PartVrm:
    out_pins: List[str] = field(default_factory=list)
    voltage: Optional[float] = None
    current_limit_a: Optional[float] = None
    kind: str = ""                  # "smps", "ldo", "source" or "" (found from the board)
    fsw_hz: Optional[float] = None


@dataclass
class PartCap:
    capacitance_f: Optional[float] = None
    esl_h: Optional[float] = None
    esr_ohm: Optional[float] = None


@dataclass
class PartEntry:
    supplies: List[SupplyModel] = field(default_factory=list)
    link: Optional[PartLink] = None
    vrm: Optional[PartVrm] = None
    cap: Optional[PartCap] = None
    role: str = ""


_KIND_WORDS = {"smps": "smps", "switcher": "smps", "buck": "smps", "boost": "smps",
               "ldo": "ldo", "linear": "ldo", "source": "source"}


def vrm_kind(text) -> str:
    """A VRM type from a ``PI_VRM`` field or a library entry ('switcher', 'smps', 'ldo',
    'source'...), or '' if it is not one."""
    return _KIND_WORDS.get(str(text or "").strip().lower(), "")


def _float(d: dict, key: str, where: str) -> Optional[float]:
    v = d.get(key)
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise AutofillError(f"{where}: {key} must be a number")
    return float(v)


def _entry(key: str, d) -> PartEntry:
    where = f"{LIB_NAME} part {key}"
    if not isinstance(d, dict):
        raise AutofillError(f"{where}: must be a mapping")
    e = PartEntry(role=str(d.get("role") or "").lower())
    if e.role and e.role not in ROLES:
        raise AutofillError(f"{where}: role must be one of {', '.join(ROLES)}")
    try:
        e.supplies = [_supply(s, i) for i, s in enumerate(d.get("supplies") or [])]
    except ModelError as err:
        raise AutofillError(f"{where}: {err}") from err
    if isinstance(d.get("link"), dict):
        k = d["link"]
        e.link = PartLink(_float(k, "resistance_ohm", where), _float(k, "current_max_a", where),
                          _float(k, "power_max_w", where))
    if isinstance(d.get("vrm"), dict):
        v = d["vrm"]
        e.vrm = PartVrm([str(p) for p in v.get("out_pins") or []], _float(v, "voltage", where),
                        _float(v, "current_limit_a", where), vrm_kind(v.get("kind")),
                        _float(v, "fsw_hz", where))
        if v.get("kind") and not e.vrm.kind:
            raise AutofillError(f"{where}: vrm kind must be smps, ldo or source")
    if isinstance(d.get("cap"), dict):
        c = d["cap"]
        e.cap = PartCap(_float(c, "capacitance_f", where), _float(c, "esl_h", where),
                        _float(c, "esr_ohm", where))
    return e


@dataclass
class PartsLibrary:
    parts: Dict[str, PartEntry] = field(default_factory=dict)
    files: List[Path] = field(default_factory=list)       # the files read, in order

    @staticmethod
    def from_dict(d) -> "PartsLibrary":
        if not isinstance(d, dict) or LIB_KEY not in d:
            raise AutofillError(f"not a KiPI-SI parts library (it has no {LIB_KEY} key)")
        if not isinstance(d[LIB_KEY], int) or d[LIB_KEY] > LIB_FORMAT:
            raise AutofillError("the parts library is from a newer version of KiPI-SI")
        parts = d.get("parts") or {}
        if not isinstance(parts, dict):
            raise AutofillError("parts must be a mapping of part number to entry")
        return PartsLibrary({str(k).strip(): _entry(str(k), v) for k, v in parts.items()})

    @staticmethod
    def load(paths: Sequence[Path]) -> "PartsLibrary":
        """The parts in every file of ``paths`` that exists; a later file's entry replaces
        an earlier one's."""
        from kipi_si.core import yaml_io
        lib = PartsLibrary()
        for path in paths:
            path = Path(path)
            if not path.is_file():
                continue
            try:
                data = yaml_io.loads(path.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001 - PyYAML's errors have no one base class here
                raise AutofillError(f"{path}: not valid YAML: {e}") from e
            try:
                lib.parts.update(PartsLibrary.from_dict(data).parts)
            except AutofillError as e:
                raise AutofillError(f"{path}: {e}") from e
            lib.files.append(path)
        return lib

    def key_of(self, fp: Footprint) -> str:
        """The part number ``fp`` is looked up by: its MPN field, else its value."""
        for name in MPN_FIELDS:
            v = (fp.fields.get(name) or "").strip()
            if v:
                return v
        return (fp.value or "").strip()

    def lookup(self, fp: Footprint) -> Optional[PartEntry]:
        key = self.key_of(fp)
        return self.parts.get(key) or self.parts.get((fp.value or "").strip())


def user_library_path() -> Path:
    """The parts library shared by every project: in KiPI-SI's folder of the user's config."""
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME") or \
        str(Path.home() / ".config")
    return Path(base) / "kipi_si" / LIB_NAME


def library_paths(project_dir: str) -> List[Path]:
    """Where the parts library is read from, the one that wins last: the user's, then the
    project's."""
    paths = [user_library_path()]
    if project_dir:
        paths.append(Path(project_dir) / LIB_NAME)
    return paths


def part_voltage(fp: Footprint, entry: Optional[PartEntry], net: str
                 ) -> Tuple[Optional[float], str]:
    """A source's or regulator's output voltage on ``net`` and where it came from: its
    ``PI_V`` field, the library, the net's name, else (None, "")."""
    v = parse_quantity(fp.fields.get("PI_V", ""), "V")
    if v is not None:
        return v, "PI_V"
    if entry and entry.vrm and entry.vrm.voltage is not None:
        return entry.vrm.voltage, "library"
    v = voltage_from_name(net)
    return (v, "net name") if v is not None else (None, "")


# ---------------------------------------------------------------------------
# The walk
# ---------------------------------------------------------------------------

@dataclass
class MissingPart:
    """A part the library and fields say nothing needed about: one stub per part number."""
    key: str
    kind: str                       # "load", "link" or "cap"
    refs: List[str] = field(default_factory=list)
    pins: List[str] = field(default_factory=list)
    net: str = ""


@dataclass
class AutofillResult:
    setup: PISetup
    notes: List[str]
    nets: List[str]                 # the rail's nets: the rail and those beyond its links
    missing: List[MissingPart]


class _Walker:
    """``vrm``: the rail's VRM, already made (by Auto-fill power tree), instead of a source
    on ``source_ref``. ``taken``: parts the walk passes over (the VRM's own, other
    switchers' inductors). ``feeds``: (part, net) of each VRM's input pins, not loads on
    the net, as the VRM draws its input current itself. ``stop``: nets another VRM drives
    or switches, which the walk does not follow a series part into. ``switches``: part ->
    (net in, net out) of the transistors that switch a rail on to another, followed as DC
    connections through them."""

    def __init__(self, snap: BoardSnapshot, rail: str, source_ref: str,
                 library: PartsLibrary, include_ground: bool, max_link_ohm: float,
                 vrm: Optional[Vrm] = None, taken=(), feeds=(), stop=(), switches=None):
        self.snap, self.rail, self.source_ref = snap, rail, source_ref
        self.lib, self.include_ground, self.max_link_ohm = library, include_ground, max_link_ohm
        self.vrm, self.taken, self.feeds, self.stop = vrm, set(taken), set(feeds), set(stop)
        self.switches: Dict[str, Tuple[str, str]] = dict(switches or {})
        self.fps = {f.reference: f for f in snap.footprints}
        self.notes: List[str] = []
        self.missing: Dict[str, MissingPart] = {}
        self.not_followed: List[str] = []
        self.dnp: List[str] = []
        self.vrms: List[Vrm] = []
        self.loads: List[Load] = []
        self.links: List[DcLink] = []
        self.caps: List[str] = []           # capacitors from the rail's nets to a ground
        self.names: set = set()
        self.grounds: set = set()

    # -------------------------------------------------------------- helpers
    def _fp(self, ref: str) -> Footprint:
        return self.fps.get(ref) or Footprint(ref, ref, "", (0.0, 0.0), "top")

    def _field(self, ref: str, name: str) -> str:
        return (self._fp(ref).fields.get(name) or "").strip()

    def _entry(self, ref: str) -> Optional[PartEntry]:
        return self.lib.lookup(self._fp(ref))

    def _role(self, ref: str) -> str:
        role = self._field(ref, "PI_ROLE").lower()
        if role and role not in ROLES:
            self.notes.append(f"{ref}: PI_ROLE '{role}' is not one of {', '.join(ROLES)}")
            role = ""
        e = self._entry(ref)
        return role or (e.role if e else "")

    def _name(self, ref: str) -> str:
        v = self._fp(ref).value
        base = f"{ref} {v}".strip() if v and v != ref else ref
        name, n = base, 2
        while name in self.names:
            name, n = f"{base} ({n})", n + 1
        self.names.add(name)
        return name

    def _is_ground(self, net: str) -> bool:
        return looks_like_ground(self.snap, net)

    def _ground(self, supply: PinRef) -> Optional[PinRef]:
        if not self.include_ground:
            return None
        g = guess_ground_pins(self.snap, None, None, supply)
        if g is not None:
            self.grounds.add(g.net)
        return g

    def _miss(self, ref: str, kind: str, net: str, pins: List[str]):
        key = self.lib.key_of(self._fp(ref)) or ref
        m = self.missing.setdefault(key, MissingPart(key, kind, net=net, pins=list(pins)))
        m.refs.append(ref)

    # -------------------------------------------------------------- items
    def source(self):
        nets = part_nets(self.snap, self.source_ref)
        if self.source_ref not in self.fps:
            raise AutofillError(f"the board has no part {self.source_ref}")
        if self.rail not in nets:
            raise AutofillError(f"{self.source_ref} has no pads on {self.rail}")
        e = self._entry(self.source_ref)
        pins = pins_on(self.snap, self.source_ref, self.rail, e.vrm.out_pins) \
            if e and e.vrm else []
        voltage = part_voltage(self._fp(self.source_ref), e, self.rail)[0]
        if voltage is None:
            if voltage is None:
                voltage = 1.0
                self.notes.append(f"{self.source_ref}: voltage not known, set to 1 V; set it "
                                  "on the VRMs tab or as vrm: voltage in the library")
        limit = parse_quantity(self._field(self.source_ref, "PI_IMAX"), "A")
        if limit is None and e and e.vrm:
            limit = e.vrm.current_limit_a
        out = PinRef(self.source_ref, self.rail, pins)
        self.vrms.append(Vrm(name=self._name(self.source_ref), output=out, voltage=voltage,
                             kind="source", ground=self._ground(out), current_limit_a=limit))

    def link_resistance(self, ref: str) -> Optional[float]:
        r = parse_ohms(self._field(ref, "PI_R"))
        e = self._entry(ref)
        if r is None and e and e.link:
            r = e.link.resistance_ohm
        if r is None and ref[:1] == "R":
            r = parse_resistance(part_value(self._fp(ref), parse_resistance))
        return r

    def try_link(self, ref: str, net: str, nets: Dict[str, List[str]],
                 role: str) -> Union[str, bool, None]:
        """The far net if ``ref`` is a series part out of ``net`` (added as a link); False
        for a resistor too big to be one (noted); None for neither."""
        if len(nets) != 2 or role in ("load", "vrm"):
            return None
        far = next(n for n in nets if n != net)
        if self._is_ground(far) or (is_capacitor_ref(ref) and role != "link"):
            return None
        e = self._entry(ref)
        r = self.link_resistance(ref)
        bead = (role == "link" or bool(e and e.link) or is_inductor_ref(ref)
                or bool(_BEAD_REF_RE.match(ref)))
        if not bead:
            if ref[:1] != "R" or r is None:
                return None
            if r > self.max_link_ohm:
                self.not_followed.append(ref)
                return False
        if r is None:
            r = 0.0
            self.notes.append(f"{ref}: no DC resistance (PI_R or the library), taken as a short")
            self._miss(ref, "link", net, nets[net])
        self.links.append(DcLink(self._name(ref), PinRef(ref, net, list(nets[net])),
                                 PinRef(ref, far, list(nets[far])), r))
        return far

    def try_switch(self, ref: str, net: str, nets: Dict[str, List[str]]) -> Optional[str]:
        """The far net of a switch transistor out of ``net`` (added as a link), or None."""
        a, b = self.switches[ref]
        if net not in (a, b) or a not in nets or b not in nets:
            return None
        far = b if net == a else a
        r = self.link_resistance(ref)
        if r is None:
            r = 0.0
            self.notes.append(f"{ref}: a switch from {a} to {b}, its on-resistance not known "
                              "(PI_R), taken as a short")
        self.links.append(DcLink(self._name(ref), PinRef(ref, net, list(nets[net])),
                                 PinRef(ref, far, list(nets[far])), r))
        return far

    def load(self, ref: str, net: str, pins: List[str], regulator: bool = False):
        supply = PinRef(ref, net, list(pins))
        load = Load(self._name(ref), supply, 0.0, ground=self._ground(supply))
        total, groups = parse_pin_currents(self._field(ref, "PI_I"))
        if self._field(ref, "PI_I") and total is None and not groups:
            self.notes.append(f"{ref}: PI_I '{self._field(ref, 'PI_I')}' can't be read")
        groups = [PinGroup([p for p in g.pins if p in pins], g.current) for g in groups]
        groups = [g for g in groups if g.pins]
        got = False
        if groups:
            load.groups, got = groups, True
        elif total is not None:
            load.current, got = total, True
        else:
            e = self._entry(ref)
            i = best_supply(LoadModel(supplies=e.supplies), load.name, supply) \
                if e and e.supplies else None
            if i is not None:
                s = e.supplies[i]
                if s.pins:
                    load.supply.pins = [p for p in s.pins if p in pins] or load.supply.pins
                done = apply_to_load(load, s)
                got = "current" in done or "pin groups" in done
        tol = parse_tolerance(self._field(ref, "PI_TOL"))
        if tol is not None:
            load.tol_min, load.tol_max = tol[0], tol[1]
            load.tol_pct, load.tol_dv = tol[2] == PERCENT, tol[2] == DELTA_VOLTS
        if not got:
            what = "regulator fed by it, its input current" if regulator else "no current"
            self.notes.append(f"{ref} on {net}: {what} (PI_I or the library), taken as 0 A")
            self._miss(ref, "load", net, pins)
        self.loads.append(load)

    # -------------------------------------------------------------- walk
    def run(self) -> List[str]:
        if self.vrm is None:
            self.source()
        else:
            self.vrms.append(self.vrm)
            self.names.add(self.vrm.name)
        refs_on: Dict[str, List[str]] = {}
        for p in self.snap.pads:
            if p.net and p.footprint:
                refs_on.setdefault(p.net, [])
                if p.footprint not in refs_on[p.net]:
                    refs_on[p.net].append(p.footprint)
        done = {self.source_ref} | self.taken
        seen, todo = [self.rail], deque([self.rail])
        while todo:
            net = todo.popleft()
            for ref in refs_on.get(net, []):
                if ref in done:
                    continue
                done.add(ref)
                role = self._role(ref)
                if role == "ignore" or (_TP_REF_RE.match(ref) and not role):
                    continue
                if self._fp(ref).dnp and not role:
                    self.dnp.append(ref)
                    continue
                if (ref, net) in self.feeds:
                    self.notes.append(f"{ref} on {net}: a VRM's input, its current from the "
                                      "VRM's load, not a load of its own")
                    continue
                nets = part_nets(self.snap, ref)
                far = self.try_switch(ref, net, nets) if ref in self.switches else None
                far = far or self.try_link(ref, net, nets, role)
                if far and far in self.stop:
                    self.notes.append(f"{ref}: joins {net} to {far}, another VRM's; not followed")
                    continue
                if far:
                    if far not in seen:
                        seen.append(far)
                        todo.append(far)
                    continue
                if far is False:
                    continue
                if is_capacitor_ref(ref) and not role:
                    if len(nets) == 2 and any(self._is_ground(n) for n in nets if n != net):
                        self.caps.append(ref)
                    continue
                if ref[:1] == "R" and len(nets) == 2 and not role:
                    continue                # a resistor to ground or a signal: no load
                e = self._entry(ref)
                self.load(ref, net, nets[net], regulator=role == "vrm" or bool(e and e.vrm))
        if self.not_followed:
            self.notes.append(f"Not followed, over {self.max_link_ohm:g} Ω: "
                              + ", ".join(sorted(self.not_followed)))
        if self.dnp:
            self.notes.append("Left out, not fitted (DNP): "
                              + ", ".join(sorted(self.dnp, key=_ref_key)))
        return seen


def _cap_models(w: _Walker, taken: Dict[str, CapModel]) -> List[CapModel]:
    """AC models for the walk's capacitors not in a model of ``taken`` (model name -> it):
    one per value and package, filled from the fields, the library and the package (see
    the module's docstring). Parts joining a model of ``taken`` with the same name and
    values are added to it instead."""
    groups: Dict[tuple, Tuple[str, List[str]]] = {}
    estimated = set()                   # groups whose ESR is a typical MLCC's
    for ref in w.caps:
        fp = w._fp(ref)
        e = w._entry(ref)
        lib = e.cap if e and e.cap else PartCap()
        value = part_value(fp, parse_capacitance)
        farads = parse_capacitance(value) or lib.capacitance_f
        esl = parse_quantity(w._field(ref, "PI_ESL"), "H")
        if esl is None:
            esl = lib.esl_h
        if esl is None:
            got = part_esl(w.snap, ref)
            esl = got[0] if got else None
        esr = parse_ohms(w._field(ref, "PI_ESR"))
        src_r = "PI_ESR"
        if esr is None and lib.esr_ohm is not None:
            esr, src_r = lib.esr_ohm, "library"
        if esr is None and farads and is_mlcc(fp.footprint, value, farads):
            esr, src_r = mlcc_esr_ohm(farads), "MLCC estimate"
        if esr is None or esl is None or not farads:
            w._miss(ref, "cap", "", [])
        size = fp.footprint.split(":")[-1]
        code = re.search(r"\d{4}(?=_\d{4}Metric)", size) or re.search(r"(?<!\d)\d{4}(?!\d)", size)
        size = code.group(0) if code and chip_length_mm(fp.footprint) else ""
        key = (value or "?", size, farads or 0.0, esl or 0.0, esr or 0.0)
        name = f"{value or ref} {size}".strip()
        groups.setdefault(key, (name, []))[1].append(ref)
        if src_r == "MLCC estimate":
            estimated.add(key)
    out: List[CapModel] = []
    names = set(taken)
    for key, (name, refs) in sorted(groups.items(), key=lambda kv: kv[1][0]):
        value, _size, farads, esl, esr = key
        refs = sorted(refs, key=_ref_key)
        same = taken.get(name)
        if same is not None and (same.capacitance_f, same.esl_h, same.esr_ohm) == \
                (farads, esl, esr):
            same.refs += refs
            continue
        n, base = 2, name
        while name in names:
            name, n = f"{base} ({n})", n + 1
        names.add(name)
        diel = parse_dielectric(value)
        rated = parse_voltage_rating(value)
        out.append(CapModel(name, farads, esl, esr, refs,
                            rated_v=rated if is_class2(value) else None, dielectric=diel,
                            aging_pct_per_decade=AGING_PCT_PER_DECADE.get(diel, 0.0)))
        unknown = [what for what, v in (("capacitance", farads), ("ESL", esl), ("ESR", esr))
                   if not v]
        refs_text = ", ".join(refs[:6]) + (" ..." if len(refs) > 6 else "")
        if unknown:
            w.notes.append(f"Capacitors {refs_text} ({name}): no {', '.join(unknown)} (PI_ESL, "
                           "PI_ESR or the library); fill it in on the AC Capacitors tab")
        if key in estimated:
            w.notes.append(f"Capacitors {refs_text} ({name}): ESR {esr * 1e3:.3g} mΩ is a "
                           "typical MLCC's, not the part's; set PI_ESR or the library for it")
    return out


def _ref_key(ref: str):
    """U2 before U10 before U1001_1: reference designators in their natural order."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", ref)]


def _merge(base: Optional[PISetup], w: _Walker, nets: List[str]) -> PISetup:
    """``base`` with this rail's VRMs, loads and links replaced by the walk's; the other
    rails, settings, thermal, AC and the stackup kept."""
    setup = copy.deepcopy(base) if base is not None else PISetup()
    group = set(nets)
    vrms = [v for v in setup.vrms if v.output.net not in group]
    loads = [l for l in setup.loads if l.supply.net not in group]
    links = [k for k in setup.links if k.side_a.net not in group and k.side_b.net not in group]
    # A part on two rails (a level shifter on 1V8 and 3V3) is named the same by each walk:
    # this walk's item takes its net in its name.
    kept = {x.name for x in [*vrms, *loads, *links]}
    for x, net in [*((v, v.output.net) for v in w.vrms), *((l, l.supply.net) for l in w.loads),
                   *((k, k.side_a.net) for k in w.links)]:
        if x.name in kept:
            name, n = f"{x.name} ({net})", 2
            while name in kept:
                name, n = f"{x.name} ({net}) ({n})", n + 1
            x.name = name
        kept.add(x.name)
    # Capacitors a model has already keep it: it may hold datasheet values set by hand.
    have = {r for m in setup.caps for r in m.refs}
    w.caps = [r for r in w.caps if r not in have]
    setup.caps = setup.caps + _cap_models(w, {m.name: m for m in setup.caps})
    setup.vrms = vrms + w.vrms
    setup.loads = loads + sorted(w.loads, key=lambda l: _ref_key(l.supply.ref))
    setup.links = links + sorted(w.links, key=lambda k: _ref_key(k.side_a.ref))
    ticked = list(setup.nets or [])
    setup.nets = ticked + [n for n in [*nets, *sorted(w.grounds)] if n not in ticked]
    return setup


def _rail_group(setup: PISetup, vrm: Vrm) -> set:
    """``vrm``'s rail: its output net and the nets beyond its series links, the group
    :func:`autofill_rail` fills. The walk stops at a net another VRM drives; empty if
    another drives ``vrm``'s own."""
    others = {v.output.net for v in setup.vrms if v is not vrm}
    start = vrm.output.net
    if start in others:
        return set()
    group, todo = {start}, deque([start])
    while todo:
        net = todo.popleft()
        for k in setup.links:
            for a, b in ((k.side_a.net, k.side_b.net), (k.side_b.net, k.side_a.net)):
                if a == net and b not in group and b not in others:
                    group.add(b)
                    todo.append(b)
    return group


def rail_parts(setup: PISetup, vrm: Vrm) -> Tuple[List[Load], List[DcLink]]:
    """The loads and series links on ``vrm``'s rail (:func:`_rail_group`), for removing
    them with the VRM."""
    group = _rail_group(setup, vrm)
    loads = [l for l in setup.loads if l.supply.net in group]
    links = [k for k in setup.links if k.side_a.net in group and k.side_b.net in group]
    return loads, links


def rail_caps(snap: BoardSnapshot, setup: PISetup, vrm: Vrm) -> List[str]:
    """The capacitors with an AC model from ``vrm``'s rail (:func:`_rail_group`) to a
    ground, as :func:`autofill_rail` adds them, for removing them with the VRM."""
    group = _rail_group(setup, vrm)
    if not group:
        return []
    out = []
    for m in setup.caps:
        for ref in m.refs:
            nets = list(part_nets(snap, ref))
            if len(nets) == 2 and any(n in group for n in nets) and \
                    any(looks_like_ground(snap, n) for n in nets if n not in group):
                out.append(ref)
    return sorted(out, key=_ref_key)


def source_candidates(snap: BoardSnapshot, rail: str,
                      library: Optional[PartsLibrary] = None) -> List[str]:
    """The parts that could drive ``rail``, likeliest first: a regulator Auto-fill power
    tree finds driving it (a switcher's device need not be on the rail itself), then one
    the library calls a regulator, then a regulator-looking part (U, VR, PS) with pads on
    another power net, then a connector (J, P, CN), then the rest. A part with signals to
    other parts on two rails (a level translator) is a load, not a source, and goes last,
    after only a regulator fed from the rail.
    Capacitors, resistors, beads, inductors and test points are left out."""
    from kipi_si.dc.pi.importers.tree_autofill import _Board, find_tree
    library = library or PartsLibrary()
    tree = find_tree(snap, library)
    found = [f.ref for f in tree if f.rail == rail and f.kind in ("ldo", "smps")]
    fed = {f.ref for f in tree if f.kind in ("ldo", "smps") and (f.ref, rail) in f.feeds()}
    b = _Board(snap, library)
    refs = sorted({p.footprint for p in snap.items_on_net(rail)[2] if p.footprint},
                  key=_ref_key)

    def score(ref: str) -> int:
        if ref in fed:
            return 4
        fp = b.fps.get(ref)
        e = library.lookup(fp) if fp else None
        if e and (e.vrm or e.role == "vrm"):
            return 0
        nets = part_nets(snap, ref)
        others = [n for n in nets if n != rail and not looks_like_ground(snap, n)]
        if re.match(r"^(U|VR|PS|IC)\d", ref) and others:
            rails = [n for n in nets if b.is_rail(n, ref)]
            return 3 if len(b.signals(ref, rails)) > 1 else 1
        if re.match(r"^(J|P|CN|X)\d", ref):
            return 2
        return 3

    skip = re.compile(r"^(C|R|L|FB|FL|TP|D)\d")
    rest = sorted((r for r in refs if not skip.match(r) and r not in found), key=score)
    return list(dict.fromkeys(found)) + rest


def autofill_rail(snap: BoardSnapshot, rail: str, source_ref: str,
                  base: Optional[PISetup] = None, library: Optional[PartsLibrary] = None,
                  include_ground: bool = False,
                  max_link_ohm: float = DEFAULT_MAX_LINK_OHM) -> AutofillResult:
    """The setup ``base`` with the power tree of ``rail``, driven by part ``source_ref``,
    filled from the board; see the module's docstring."""
    if not any(n.name == rail for n in snap.nets):
        raise AutofillError(f"the board has no net {rail}")
    if library is None:
        library = PartsLibrary.load(library_paths(snap.project_dir))
    # A regulator Auto-fill power tree recognises is made as one (a switcher with its
    # input, its inductor's pins on the rail), not as a source.
    from kipi_si.dc.pi.importers.tree_autofill import regulator_for, to_vrm
    reg = regulator_for(snap, rail, source_ref, library)
    # A part that is another VRM's input draws its current through that VRM.
    feeds = {(ph.input.ref, ph.input.net) for v in (base.vrms if base else [])
             if v.output.net != rail for ph in v.all_phases() if ph.input is not None}
    w = _Walker(snap, rail, source_ref, library, include_ground, max_link_ohm,
                taken=(reg.refs() | set(reg.inductors)) if reg else (), feeds=feeds)
    if reg is not None:
        if reg.voltage is None:
            w.notes.append(f"{source_ref}: voltage not known, set to 1 V; set it on the "
                           "VRMs tab, as PI_V or as vrm: voltage in the library")
        w.vrm = to_vrm(reg, w._name(source_ref), include_ground)
        w.notes.append(f"{source_ref}: {reg.why}")
    nets = w.run()
    return AutofillResult(_merge(base, w, nets), w.notes, nets, list(w.missing.values()))


# ---------------------------------------------------------------------------
# Ratings, after a solve
# ---------------------------------------------------------------------------

def link_ratings(snap: BoardSnapshot, setup: PISetup,
                 library: Optional[PartsLibrary] = None) -> Dict[str, Tuple[Optional[float],
                                                                             Optional[float]]]:
    """{link name: (current rating A, power rating W)} for the links whose part has either,
    from its ``PI_IMAX`` / ``PI_PMAX`` fields or the library."""
    if library is None:
        library = PartsLibrary.load(library_paths(snap.project_dir))
    fps = {f.reference: f for f in snap.footprints}
    out = {}
    for k in setup.links:
        fp = fps.get(k.side_a.ref)
        if fp is None:
            continue
        e = library.lookup(fp)
        imax = parse_quantity(fp.fields.get("PI_IMAX", ""), "A")
        pmax = parse_quantity(fp.fields.get("PI_PMAX", ""), "W")
        if e and e.link:
            imax = e.link.current_max_a if imax is None else imax
            pmax = e.link.power_max_w if pmax is None else pmax
        if imax is not None or pmax is not None:
            out[k.name] = (imax, pmax)
    return out


def rating_checks(tree, snap: BoardSnapshot, setup: PISetup,
                  library: Optional[PartsLibrary] = None) -> List[Tuple[str, bool]]:
    """(line, passed) for each solved series part with a rating: its current against its
    current rating and its loss against its power rating. ``tree`` is a
    :class:`~kipi_si.dc.pi.results.TreeResult`."""
    ratings = link_ratings(snap, setup, library)
    out = []
    for g in tree.groups.values():
        for s in g.result.fields.series:
            if s.name not in ratings or math.isnan(s.current):
                continue
            imax, pmax = ratings[s.name]
            bits, ok = [], True
            if imax:
                ok &= abs(s.current) <= imax
                bits.append(f"{abs(s.current):.3g} A of {imax:g} A "
                            f"({100 * abs(s.current) / imax:.0f} %)")
            if pmax:
                ok &= abs(s.power) <= pmax
                bits.append(f"{abs(s.power) * 1e3:.3g} mW of {pmax * 1e3:g} mW "
                            f"({100 * abs(s.power) / pmax:.0f} %)")
            if bits:
                out.append((f"{s.name}: {', '.join(bits)}", bool(ok)))
    return out


# ---------------------------------------------------------------------------
# Stubs for the parts with no data
# ---------------------------------------------------------------------------

def _stub_lines(m: MissingPart) -> List[str]:
    def q(s):
        return "'" + str(s).replace("'", "''") + "'"
    lines = [f"  {q(m.key)}:    # {', '.join(m.refs[:6])}{' ...' if len(m.refs) > 6 else ''}"]
    if m.kind == "link":
        lines.append("    link: {resistance_ohm: null, current_max_a: null, power_max_w: null}")
    elif m.kind == "cap":
        lines.append("    cap: {capacitance_f: null, esl_h: null, esr_ohm: null}")
    else:
        pins = ", ".join(q(p) for p in m.pins)
        lines.append(f"    supplies:\n      - {{name: {q(m.net)}, pins: [{pins}], current_a: null}}")
    return lines


def write_stubs(path: Path, missing: List[MissingPart]) -> Tuple[Path, int]:
    """Add an entry with empty values for each part of ``missing`` not in the library at
    ``path`` yet, to fill in by hand. A new file is written whole; to an existing one
    whose last section is ``parts:`` the entries are appended, keeping its comments, else
    they go to ``pi_parts.missing.yml`` beside it. (The file written, entries added.)"""
    path = Path(path)
    have = set(PartsLibrary.load([path]).parts) if path.is_file() else set()
    new = [m for m in missing if m.key not in have]
    if not new:
        return path, 0
    body = [line for m in new for line in _stub_lines(m)]
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join([f"{LIB_KEY}: {LIB_FORMAT}", "parts:", *body]) + "\n",
                        encoding="utf-8")
        return path, len(new)
    text = path.read_text(encoding="utf-8")
    tops = [ln for ln in text.splitlines() if ln and not ln[0].isspace() and ln[0] != "#"]
    if tops and tops[-1].split(":")[0].strip() == "parts" and tops[-1].strip() != "parts: {}":
        sep = "" if text.endswith("\n") else "\n"
        path.write_text(text + sep + "\n".join(body) + "\n", encoding="utf-8")
        return path, len(new)
    other = path.with_name("pi_parts.missing.yml")
    other.write_text("\n".join([f"{LIB_KEY}: {LIB_FORMAT}", "parts:", *body]) + "\n",
                     encoding="utf-8")
    return other, len(new)
