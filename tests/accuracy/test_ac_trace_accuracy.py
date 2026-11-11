"""The AC solve's inductance of a rail trace over a ground plane, against the 2D field
solve of its cross-section.

The sheet model is a plane pair's: μ₀h per square. A trace not much wider than its height
over the plane has far less than the parallel-plate μ₀h/w, the field fringing round it;
without that the AC solve read a trace as wide as its height 1.8 times too inductive, and
one half as wide 2.8 times.
"""

import math

import numpy as np
import pytest
from shapely.geometry import box

from validation_boards import boards as vb
from kipi_si.ac.model import CapModel
from kipi_si.ac.solver import fem, solve_ac
from kipi_si.ac.solver.physics import MU0_H_PER_MM
from kipi_si.dc.pi.model import PinRef, Vrm
from kipi_si.si.materials import Dielectric
from kipi_si.si.xsection import Band, Conductor, solve

F_HZ = 1e8                     # the skin effect has the current on the faces: the 2D solve's L


def _trace_board(w, h, length):
    """A rail trace ``w`` wide and ``length`` long on F.Cu, ``h`` over a GND plane, from
    the probe U1 to C1, a short."""
    b = vb.Board("trace", vb.stackup(diel=(h, 1.0, 0.2)))
    y, x0 = 15.0, 10.0
    x1 = x0 + length
    vb._ac_part(b, "U1", (x0, y), "Probe", gap=-vb.AcPlane.GAP)
    vb._ac_part(b, "C1", (x1, y), "short")
    b.track("+3V3", vb.F, w, (x0, y), (x1, y))
    b.zone("GND", vb.IN1, box(0, 0, x1 + 10, 30))
    vrm = Vrm("VRM1", PinRef("U1", "+3V3", ["1"]), 3.3, ground=PinRef("U1", "GND", ["2"]))
    setup = vb._ac_setup([vrm], [vb._probe("U1")], [CapModel("short", 1.0, 1e-13, 1e-5, ["C1"])],
                         f_start_hz=F_HZ / 10, f_stop_hz=F_HZ, points_per_decade=1,
                         field_points_per_decade=0, max_edge_mm=0.5)
    return b.snapshot(), setup


def _loop_inductance(w, h, length):
    snap, setup = _trace_board(w, h, length)
    res = solve_ac(snap, setup, "VRM1", "GND")
    return res.probes[0].z[-1].imag / (2 * math.pi * res.freqs[-1])


def _per_mm(w, h):
    """The trace's inductance per mm: two lengths' difference, the ends' own taken off."""
    return (_loop_inductance(w, h, 30.0) - _loop_inductance(w, h, 10.0)) / 20.0


def _field_solved(w, h):
    win = max(3.0, 10 * w, 12 * h)
    conds = [Conductor.rect(-w / 2, w / 2, h, h + vb.OZ1, "s"),
             Conductor.rect(-win, win, -vb.OZ_HALF, 0.0)]
    lp = solve(conds, [Band(0, h, Dielectric(vb.ER, 0.02))], (-win, win, -win, win + h))
    return lp.l[0, 0]


@pytest.mark.parametrize("w, h", [(0.1, 0.2), (0.2, 0.2), (0.5, 0.2), (1.0, 0.2), (3.0, 0.2),
                                  (0.25, 0.5), (1.0, 0.5), (0.3, 0.1)])
def test_trace_inductance_is_the_field_solvers(w, h):
    exact = _field_solved(w, h)
    assert _per_mm(w, h) == pytest.approx(exact, rel=0.12)
    if w <= h:                      # where the parallel plate is far off
        assert MU0_H_PER_MM * h / w > 1.8 * exact


def test_a_wide_plane_is_left_a_plane():
    """Copper over :data:`fem.FRINGE_WIDE` heights wide keeps μ₀h per square."""
    assert fem.fringe_factor(fem.FRINGE_WIDE) == pytest.approx(1.0)
    assert fem.fringe_factor(1e6) == pytest.approx(1.0)
    assert fem.fringe_factor(np.inf) == pytest.approx(1.0)
    assert fem.fringe_factor(1.0) == pytest.approx(0.553)
    f = fem.fringe_factor(np.array([0.3, 0.5, 1.0, 2.0, 3.0]))
    assert np.all(np.diff(f) > 0) and f[-1] < 1.0       # narrower: more of it fringes


# ---------------------------------------------------------------- the copper's local width

def test_local_width_of_a_trace_a_neck_and_a_plane():
    plane = box(0, 0, 40, 40)
    trace = box(40, 19.75, 60, 20.25)                   # 0.5 mm wide, off the plane's edge
    slots = box(18, 0, 22, 19).union(box(18, 21, 22, 40))   # leave a 2 mm neck at y = 20
    copper = plane.difference(slots).union(trace)
    pts = np.array([[50.0, 20.0],       # in the trace
                    [50.0, 20.2],       # near its edge: as wide
                    [20.0, 20.0],       # in the neck
                    [8.0, 30.0],        # in the plane
                    [70.0, 20.0],       # off the copper
                    [20.0, 10.0]])      # in a slot
    w = fem.local_width(copper, pts, 10.0)
    step = fem.WIDTH_STEP
    assert 0.5 / step < w[0] < 0.5 * step
    assert w[1] == pytest.approx(w[0])
    assert 2.0 / step < w[2] < 2.0 * step
    assert np.isinf(w[3]) and np.isinf(w[4]) and np.isinf(w[5])


def test_local_width_keeps_a_planes_corners():
    """A sharp corner of a wide plane is plane, not narrow copper."""
    w = fem.local_width(box(0, 0, 40, 40), np.array([[0.05, 0.05], [39.9, 0.2]]), 16.0)
    assert np.all(np.isinf(w))
