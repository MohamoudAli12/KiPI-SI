"""Power integrity plots of a DC power-tree solve, drawn the same way in the PI plots view
and in a report, as :mod:`kipi_si.si.siplots` does for Signal Integrity:

* each load's voltage against its tolerance window (:func:`load_margins`);
* where each load's drop is lost: VRM, series parts, copper, ground (:func:`drop_budget`).

The data functions need no plotting library; the ``draw_*`` ones draw on a matplotlib
figure in an :class:`~kipi_si.si.siplots.Ink`'s colours.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from kipi_si.si.siplots import Ink

def _status(passed: Optional[bool]) -> Optional[str]:
    return None if passed is None else ("PASS" if passed else "FAIL")


def _pct(v: float, nominal: float) -> float:
    return 100.0 * (v - nominal) / nominal if nominal else math.nan


# ---------------------------------------------------------------------------
# 1. Each load against its tolerance
# ---------------------------------------------------------------------------

@dataclass
class LoadMargin:
    name: str
    group: str
    nominal: float
    v_mean: float                  # effective: supply minus ground, mean over the pins
    v_low: float                   # the lowest pin
    v_high: float                  # the highest pin
    limit_low: Optional[float]
    limit_high: Optional[float]
    status: Optional[str]          # PASS, FAIL or None (no tolerance set, not solved)

    def pct(self, v: Optional[float]) -> float:
        """``v`` as % from nominal (NaN for None)."""
        return math.nan if v is None else _pct(v, self.nominal)


def load_margins(tree) -> List[LoadMargin]:
    """Each solved load's voltages and tolerance window; loads with no voltage (not
    connected to their VRM) are left out."""
    out = []
    for l in tree.loads:
        if not l.nominal or not math.isfinite(l.v_effective):
            continue
        low = l.v_low if l.v_low is not None else l.v_effective
        high = l.v_high if l.v_high is not None else l.v_effective
        out.append(LoadMargin(l.name, l.group, l.nominal, l.v_effective, low, high,
                              l.limit_low, l.limit_high, _status(l.passed)))
    return out


def draw_loads(fig, rows: Sequence[LoadMargin], ink: Ink, style=None):
    """A row per load, in % of its nominal voltage: the tolerance window shaded, the
    worst pins as a bar from the lowest to the highest, the mean as a dot, coloured by
    the load's verdict."""
    fig.clear()
    ax = fig.add_subplot(111)
    y = np.arange(len(rows))
    for k, r in enumerate(rows):
        lo, hi = r.pct(r.limit_low), r.pct(r.limit_high)
        if math.isfinite(lo) or math.isfinite(hi):
            a = lo if math.isfinite(lo) else min(r.pct(r.v_low), 0.0) - 1.0
            b = hi if math.isfinite(hi) else max(r.pct(r.v_high), 0.0) + 1.0
            ax.barh(k, b - a, left=a, height=0.8, color=ink.status[0], alpha=0.15,
                    edgecolor="none")
            for x in (lo, hi):
                if math.isfinite(x):
                    ax.plot([x, x], [k - 0.4, k + 0.4], color=ink.faint, lw=1.0)
        color = ink.of(r.status)
        # The pins' span, with its ends marked: a load on one pin has no span to see.
        ax.plot([r.pct(r.v_low), r.pct(r.v_high)], [k, k], color=color, lw=5,
                solid_capstyle="butt", marker="D", ms=7)
        ax.plot([r.pct(r.v_mean)], [k], "o", color=ink.text, ms=4)
    ax.axvline(0, color=ink.faint, lw=0.8)
    ax.set_yticks(y, [f"{r.name}  ({r.group})" for r in rows], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Voltage at the load, % from nominal (bar: lowest to highest pin; "
                  "dot: mean; shaded: tolerance)")
    if style is not None:
        style(ax)
    ax.grid(False, axis="y")
    ax.set_axisbelow(True)
    return ax


# ---------------------------------------------------------------------------
# 2. Where each load's drop goes
# ---------------------------------------------------------------------------

BUDGET_PARTS = ("VRM output", "Series parts", "Copper", "Ground return")


@dataclass
class DropBudget:
    name: str
    group: str
    nominal: float
    parts: Dict[str, float] = field(default_factory=dict)   # volts, by BUDGET_PARTS
    links: List[str] = field(default_factory=list)          # the series parts on its path

    @property
    def total(self) -> float:
        return sum(self.parts.values())


def _path_links(start: str, goal: str, links) -> Optional[List]:
    """The series links on the shortest chain of nets from ``start`` to ``goal`` (None if
    they do not join)."""
    prev = {start: None}
    todo = deque([start])
    while todo:
        net = todo.popleft()
        if net == goal:
            path = []
            while prev[net] is not None:
                net, k = prev[net]
                path.append(k)
            return path[::-1]
        for k in links:
            for a, b in ((k.side_a.net, k.side_b.net), (k.side_b.net, k.side_a.net)):
                if a == net and b not in prev:
                    prev[b] = (net, k)
                    todo.append(b)
    return None


def drop_budget(tree, setup) -> List[DropBudget]:
    """Each solved load's drop (nominal minus its mean effective voltage) split into: the
    VRM's own output below its set voltage (a load line; negative for a remote-sense
    boost), the series parts on the way (their current times resistance), the copper
    (planes, traces and vias: the rest of the supply side) and the ground's rise.

    The parts add up to the drop. The series parts are those on the shortest chain of nets
    from the VRM to the load; where current shares parallel paths, their split is
    approximate and the copper takes the difference."""
    vrm_of = {v.group: v for v in tree.vrms}
    load_net = {l.name: l.supply.net for l in getattr(setup, "loads", [])}
    vrm_net = {v.name: v.output.net for v in getattr(setup, "vrms", [])}
    links = list(getattr(setup, "links", []))
    series = {s.name: s for g in tree.groups.values() for s in g.result.fields.series}
    out = []
    for l in tree.loads:
        if not l.nominal or not math.isfinite(l.v_effective):
            continue
        v = vrm_of.get(l.group)
        g = tree.groups.get(l.group)
        if g is not None and g.driver in vrm_net:
            v = next((x for x in tree.vrms if x.name == g.driver), v)
        v_out = v.v_out if v is not None and math.isfinite(v.v_out) else l.nominal
        ground = l.v_ground or 0.0
        on_path, through = 0.0, []
        start, goal = vrm_net.get(v.name if v else ""), load_net.get(l.name)
        if start and goal:
            for k in _path_links(start, goal, links) or []:
                s = series.get(k.name)
                if s is not None and math.isfinite(s.current):
                    on_path += abs(s.current) * s.resistance
                    through.append(k.name)
        supply = v_out - l.v_supply
        out.append(DropBudget(l.name, l.group, l.nominal, {
            "VRM output": l.nominal - v_out, "Series parts": on_path,
            "Copper": supply - on_path, "Ground return": ground}, through))
    return out


def draw_budget(fig, rows: Sequence[DropBudget], ink: Ink, style=None):
    """A stacked bar per load, in mV: where its drop is lost."""
    fig.clear()
    ax = fig.add_subplot(111)
    y = np.arange(len(rows))
    pos, neg = np.zeros(len(rows)), np.zeros(len(rows))
    for i, part in enumerate(BUDGET_PARTS):
        vals = np.array([r.parts.get(part, 0.0) * 1e3 for r in rows])
        left = np.where(vals >= 0, pos, neg)
        ax.barh(y, vals, left=left, height=0.6, color=ink.colors[i % len(ink.colors)],
                label=part)
        pos += np.clip(vals, 0, None)
        neg += np.clip(vals, None, 0)
    for k, r in enumerate(rows):
        ax.text(max(pos[k], 0.0), k, f"  {r.total * 1e3:.3g} mV", va="center", fontsize=7,
                color=ink.text)
    ax.axvline(0, color=ink.faint, lw=0.8)
    ax.set_yticks(y, [f"{r.name}  ({r.group})" for r in rows], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Drop at the load, mV (mean over its pins)")
    span = max(float(pos.max()) if len(rows) else 0.0, 1e-6)
    ax.set_xlim(min(float(neg.min()) if len(rows) else 0.0, 0.0) * 1.1, span * 1.25)
    if style is not None:
        style(ax)
    ax.grid(False, axis="y")
    ax.set_axisbelow(True)
    return ax
