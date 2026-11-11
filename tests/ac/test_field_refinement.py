"""The sweep's adaptive field solves (:func:`kipi_si.ac.solver.sweep.refine_field`): more
frequencies where the interpolation between the solved ones does not hold."""

import numpy as np
import pytest

from kipi_si.ac.solver.sweep import (FIELD_TOL, _interpolate, interpolation_error,
                                     refine_field)

C, L, R, C2 = 1e-9, 1e-9, 0.3, 5e-11   # a plane's capacitance, and one resonance beside it
F0 = 1 / (2 * np.pi * np.sqrt(L * C2))
SWEEP = np.logspace(8, 9.5, 376)       # 250 points a decade


def _smooth(f):
    return np.array([[1 / (2j * np.pi * f * C)]])


def _resonant(f):
    w = 2 * np.pi * f
    return _smooth(f) + 1 / (1j * w * C2 + 1 / (R + 1j * w * L))


def _solved(z, f):
    return np.array([z(x) for x in f])


def test_a_capacitor_needs_nothing_more():
    f = np.logspace(5, 9, 41)
    f2, z2, note = refine_field(_smooth, f, _solved(_smooth, f), np.logspace(5, 9, 1001))
    assert len(f2) == len(f) and note == ""
    assert interpolation_error(f, _solved(_smooth, f)).max() < 1e-6


def test_a_resonance_between_the_solved_frequencies_is_found():
    f = np.logspace(8, 9.5, 16)
    zb = _solved(_resonant, f)
    assert interpolation_error(f, zb).max() > FIELD_TOL
    f2, z2, note = refine_field(_resonant, f, zb, SWEEP)
    assert note == ""
    assert np.all(np.diff(f2) > 0) and set(f) <= set(f2)
    added = np.setdiff1d(f2, f)
    near = (added > F0 / 1.5) & (added < F0 * 1.5)
    assert near.sum() > (~near).sum()                   # most of them around it
    assert np.isin(added, SWEEP).all()                  # at the sweep's own frequencies
    assert len(f2) < len(SWEEP) / 3
    assert z2 == pytest.approx(_solved(_resonant, f2))
    sweep = SWEEP
    exact = _solved(_resonant, sweep)[:, 0, 0]
    before = _interpolate(f, zb, sweep)[:, 0, 0]
    after = _interpolate(f2, z2, sweep)[:, 0, 0]
    assert np.max(np.abs(before - exact) / np.abs(exact)) > 0.2
    assert np.max(np.abs(after - exact) / np.abs(exact)) < 0.03


def test_it_stops_at_the_sweeps_points_and_says_so():
    """A sweep too coarse for the resonance is solved at its own points around it: exact
    there, with a note that it shows the resonance poorly."""
    f = np.logspace(8, 9.5, 16)
    sweep = np.logspace(8, 9.5, 31)                     # 20 points a decade
    f2, z2, note = refine_field(_resonant, f, _solved(_resonant, f), sweep)
    near = sweep[(sweep > 0.7 * F0) & (sweep < 1.4 * F0)]
    assert np.isin(near, f2).all()
    assert np.isin(np.setdiff1d(f2, f), sweep).all()
    assert "more points per decade" in note
    exact = _solved(_resonant, near)[:, 0, 0]
    assert _interpolate(f2, z2, near)[:, 0, 0] == pytest.approx(exact, rel=1e-9)


def test_it_stops_at_its_budget_and_says_so():
    f = np.logspace(8, 9.5, 16)
    f2, _, note = refine_field(_resonant, f, _solved(_resonant, f), np.logspace(8, 9.5, 3751),
                               max_extra=5)
    assert len(f2) == len(f) + 5
    assert "5 more frequencies" in note
