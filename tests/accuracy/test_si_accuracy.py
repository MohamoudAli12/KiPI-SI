"""Signal integrity against closed forms and bounds, where a default once went wrong.

* A trace's cut reaches far enough for a trace high over its reference: a 50 Ω microstrip
  on a 2-layer board read 18 Ω inside the fixed ±1.5 mm cut's grounded box.
* The statistical eye keeps a long tail of small cursors: it lies between the eye with
  every cursor against the bit (peak distortion) and the eye without them.
* An interface's edge is its 20–80 % rise time, in the step response too.
"""

import numpy as np
import pytest
from shapely.geometry import box

from validation_boards import boards as vb
from kipi_si.si import closed_form as cf
from kipi_si.si import eye as eyes
from kipi_si.si import sparams
from kipi_si.si.board import SIBoard
from kipi_si.si.model import SISettings


# ---------------------------------------------------------------- the cut's window

def _microstrip_board(w, h, two_layer):
    st = (vb.stackup((vb.OZ1, vb.OZ1), (h,)) if two_layer
          else vb.stackup(diel=(h, 0.4, h)))
    b = vb.Board("ms", st)
    b.track("SIG", vb.F, w, (10.0, 20.0), (50.0, 20.0))
    b.zone("GND", vb.B if two_layer else vb.IN1, box(0, 0, 60, 40))
    return SIBoard(b.snapshot())


@pytest.mark.parametrize("w, h, two_layer", [(2.9, 1.5, True), (1.0, 0.5, False),
                                             (0.35, 0.2, False)])
def test_microstrip_high_over_its_plane(w, h, two_layer):
    board = _microstrip_board(w, h, two_layer)
    conds, bx, _ = board.section((30.0, 20.0), (0.0, 1.0), vb.F, w, "SIG",
                                 SISettings().window_mm)
    r = board.solve(conds, bx)
    z0, ee = cf.microstrip(w, h, vb.ER, vb.OZ1)
    assert r.z0() == pytest.approx(z0, rel=0.03)
    assert r.er_eff() == pytest.approx(ee, rel=0.03)


def test_the_window_grows_with_the_height_only_when_it_must():
    thin = _microstrip_board(0.35, 0.2, False)
    _, bx, _ = thin.section((30.0, 20.0), (0.0, 1.0), vb.F, 0.35, "SIG", 1.5)
    assert bx[1] == pytest.approx(2.0)             # 0.175 + 8 × 0.2, to the next 0.5 mm
    _, bx, _ = thin.section((30.0, 20.0), (0.0, 1.0), vb.F, 0.35, "SIG", 4.0)
    assert bx[1] == pytest.approx(4.0)             # a wider window asked for is kept
    thick = _microstrip_board(2.9, 1.5, True)
    conds, bx, _ = thick.section((30.0, 20.0), (0.0, 1.0), vb.F, 2.9, "SIG", 1.5)
    assert bx[1] == pytest.approx(13.5)            # 1.45 + 8 × 1.5
    plane = max(conds[1:], key=lambda c: c.width_mm)
    assert plane.width_mm == pytest.approx(27.0)   # the plane was cut again, as wide


# ---------------------------------------------------------------- the eye's small cursors

def _tailed_pulse(n_tail, amp, spui=32, ui=1e-10):
    """A one-UI flat pulse of height 1 followed by ``n_tail`` cursors of ±``amp``."""
    v = np.zeros((n_tail + 8) * spui)
    v[4 * spui:5 * spui] = 1.0
    rng = np.random.default_rng(0)
    for k in range(1, n_tail + 1):
        v[(4 + k) * spui:(5 + k) * spui] = amp * rng.choice([-1, 1])
    return eyes.Pulse(np.arange(len(v)) * ui / spui, v, ui, spui)


@pytest.mark.parametrize("n_tail, amp", [(40, 0.0015), (40, 0.004), (100, 0.0015),
                                         (20, 0.02)])
@pytest.mark.parametrize("levels", [256, 512, 2048])
def test_small_cursors_close_the_eye(n_tail, amp, levels):
    p = _tailed_pulse(n_tail, amp)
    e = eyes.statistical_eye(p, 1e-12, levels=levels)
    dv = e.levels_v[1] - e.levels_v[0]
    worst = 1.0 - n_tail * amp                      # every cursor against the bit
    assert e.height_v >= worst - 3 * dv             # never worse than peak distortion
    assert e.height_v <= 1.0 - 0.5 * n_tail * amp   # and the tail is not lost


def test_the_equaliser_search_sees_a_reflective_tail():
    """Its eyes (fewer levels) rank a clean pulse above one with a tail of small cursors."""
    clean = eyes.statistical_eye(_tailed_pulse(40, 0.0), 1e-12, levels=256)
    tailed = eyes.statistical_eye(_tailed_pulse(40, 0.004), 1e-12, levels=256)
    assert tailed.height_v < clean.height_v - 0.08


def test_binned_cursors_keep_their_sum():
    c = np.array([0.3, -0.26, 0.004, 0.004, 0.004, -0.003, -0.003, 0.0, 0.0011])
    dv = 0.01
    s = eyes._bin_shifts(c, dv)
    assert s[c > 0].sum() * dv == pytest.approx(c[c > 0].sum(), abs=0.5 * dv)
    assert s[c < 0].sum() * dv == pytest.approx(c[c < 0].sum(), abs=0.5 * dv)
    assert np.all(s[c > 0] >= 0) and np.all(s[c < 0] <= 0) and np.all(s[c == 0] == 0)


# ---------------------------------------------------------------- the edge

def _edge(rise_s):
    """(10–90 %, 20–80 %) of the step a delayed, flat channel gives."""
    f = sparams.uniform_grid(60e9, 20e6)
    delay = 2e-9
    t, s = sparams.step(f, np.exp(-2j * np.pi * f * delay), rise_s, oversample=4)
    s = s / s[np.searchsorted(t, 2 * delay)]
    sel = (t > delay - 5 * rise_s) & (t < delay + 5 * rise_s)
    at = lambda level: float(np.interp(level, s[sel], t[sel]))  # noqa: E731
    return at(0.9) - at(0.1), at(0.8) - at(0.2)


@pytest.mark.parametrize("rise_s", [40e-12, 100e-12])
def test_the_step_rises_in_its_20_to_80_percent_time(rise_s):
    r10_90, r20_80 = _edge(rise_s)
    assert r20_80 == pytest.approx(rise_s, rel=0.03)
    assert r10_90 == pytest.approx(rise_s * 2.5631 / 1.6832, rel=0.03)


def test_the_eye_and_the_buffers_use_one_edge():
    """The generic buffer's 0–100 % edge is the interface's 20–80 % over 0.6; the linear
    eye's Gaussian edge has that same 20–80 %."""
    from kipi_si.si.solver import per_ui
    rise = 100e-12
    assert _edge(rise)[1] == pytest.approx(rise, rel=0.03)
    assert per_ui(1e-9, rise, 8, 1, 10 ** 6) == 48     # 8 samples across rise / 0.6
