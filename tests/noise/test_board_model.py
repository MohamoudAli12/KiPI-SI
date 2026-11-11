"""The board model (#69): transfer impedances between ports with the parts on, the
capacitor current split through the copper, the rails' ripple, and shared-ground
coupling onto victims."""

import numpy as np
import pytest

from kipi_si.ac.model import CapModel
from kipi_si.ac.solver.fem import PortDef
from kipi_si.ac.solver.sweep import element_currents, terminate, terminate_transfer
from kipi_si.noise.checks import seed_phases
from kipi_si.noise.model import Aggressor, Victim
from kipi_si.noise.network import Termination, VictimNetwork
from kipi_si.noise.extract.capacitive import Segment
from kipi_si.noise.solver import solve_noise
from noise_boards import buck_board, buck_setup
from synthetic import F


def _random_board(n_probe=2, n_cap=3, freqs=(1e6, 1e8), seed=1):
    """A symmetric, passive-looking port impedance matrix and its ports."""
    rng = np.random.default_rng(seed)
    p = n_probe + n_cap
    zb = []
    for f in freqs:
        a = rng.normal(size=(p, p)) + 1j * rng.normal(size=(p, p))
        z = (a @ a.conj().T) * 1e-3 + 1j * 2 * np.pi * f * 1e-9 * np.eye(p)
        zb.append(0.5 * (z + z.T))
    ports = [PortDef(f"P{i}", "probe", [], []) for i in range(n_probe)]
    ports += [PortDef(f"C{i}", "cap", [], [], CapModel(f"C{i}", 1e-6 * (i + 1), 1e-10, 1e-3))
              for i in range(n_cap)]
    return np.array(zb), np.array(freqs), ports


def test_the_transfer_diagonal_is_the_probe_impedance():
    zb, f, ports = _random_board()
    zt = terminate_transfer(zb, f, ports, [0, 1], [0, 1])
    z = terminate(zb, f, ports)
    assert np.allclose(np.diagonal(zt, axis1=1, axis2=2), z)


def test_transfer_impedance_is_reciprocal():
    zb, f, ports = _random_board()
    zt = terminate_transfer(zb, f, ports, [0, 1], [0, 1])
    assert np.allclose(zt[:, 0, 1], zt[:, 1, 0])


def test_element_currents_balance_the_source():
    """With the parts' impedances, V_E = −Z_e·I_E at every part."""
    zb, f, ports = _random_board()
    E, i = element_currents(zb, f, ports, [0])
    from kipi_si.ac.solver.sweep import element_impedance
    for k in range(len(f)):
        ie = i[k, :, 0]
        ze = np.array([element_impedance(ports[e], 2 * np.pi * f[k]) for e in E])
        v = zb[k][np.ix_(E, [0])][:, 0] + zb[k][np.ix_(E, E)] @ ie
        assert np.allclose(v, -ze * ie)


def test_a_ground_difference_drives_the_victim_through_its_driver():
    """A high-impedance receiver sees the driver's ground difference whole."""
    v = 299.792458e9 / np.sqrt(3.3)
    segs = [Segment((k * 0.5, 0.0), ((k + 1) * 0.5, 0.0), F, 0.2, 1 / (50 * v), 50 / v)
            for k in range(4)]
    net = VictimNetwork(segs, {F: 0.035})
    f = np.array([1e6])
    src = np.zeros((1, net.n), complex)
    src[0, net.nearest((0.0, 0.0))] = 0.01 / 33.0             # 10 mV behind 33 Ω
    out = net.solve_many(f, [Termination((0.0, 0.0), 33.0), Termination((2.0, 0.0), 1e6)],
                         [net.nearest((2.0, 0.0))], {"g": src})["g"]
    assert abs(out[0, 0]) == pytest.approx(0.01, rel=0.01)


def _setup(snap, victims, board_model=True, models=True):
    setup = buck_setup(board_model=board_model)
    vrm = next(v for v in setup.vrms if v.name == "U1")
    a = Aggressor("U1 buck", "U1", fsw_hz=1e6)
    a.phases = seed_phases(snap, setup, vrm, "buck")
    a.phases[0].coss_f = 300e-12
    setup.aggressors.append(a)
    if models:
        setup.caps = [CapModel("10u", 10e-6, 0.4e-9, 0.003, ["C1"]),
                      CapModel("47u", 47e-6, 0.6e-9, 0.002, ["C2"])]
    setup.victims = victims
    return setup


def test_one_capacitor_per_rail_takes_all_the_ripple():
    """With one capacitor on each rail and nothing else at AC, the board model gives each
    the whole switching current at the low harmonics, as the lumped split does."""
    snap = buck_board()
    lumped = solve_noise(snap, _setup(snap, [], board_model=False), "U1 buck").waveforms
    board = solve_noise(snap, _setup(snap, []), "U1 buck").waveforms
    for name in ("input_caps", "output_caps"):
        (ref,) = getattr(lumped, name)
        a = getattr(lumped, name)[ref].c[:10]
        b = getattr(board, name)[ref].c[:10]
        assert np.allclose(b, a, rtol=0.05, atol=1e-3 * np.abs(a).max())


def test_the_board_model_reports_itself_and_the_rails_ripple():
    snap = buck_board()
    r = solve_noise(snap, _setup(snap, []), "U1 buck")
    assert r.board_note.startswith("Board model: 2 capacitor(s)")
    assert any("Board model" in line for line in r.summary_lines())
    n = r.waveforms.samples_per_period()
    assert np.ptp(r.waveforms.input_ripple.samples(n)) > 0
    assert np.ptp(r.waveforms.output_ripple.samples(n)) > 0


def test_capacitors_without_models_get_their_board_values():
    snap = buck_board()
    r = solve_noise(snap, _setup(snap, [], models=False), "U1 buck")
    assert set(r.waveforms.input_caps) == {"C1"} and set(r.waveforms.output_caps) == {"C2"}
    assert any("taken at their value from the board" in w for w in r.warnings)


def test_shared_ground_coupling_is_a_mechanism():
    snap = buck_board(victim_gap=0.2)
    v = solve_noise(snap, _setup(snap, [Victim("SIG")]), "U1 buck").victims[0]
    assert set(v.peak_by) == {"capacitive", "inductive", "common"}
    assert v.peak_by["common"] > 0
    total = sum(v.receiver_v[k].c for k in ("capacitive", "inductive", "common"))
    assert np.allclose(v.receiver_v["total"].c, total)
    off = solve_noise(snap, _setup(snap, [Victim("SIG")], board_model=False),
                      "U1 buck").victims[0]
    assert "common" not in off.peak_by
    # The board model changes the hot loop (traced through the copper, #187), so the
    # ringing and with it the switch node differ a little; the capacitive path is the same.
    assert off.peak_by["capacitive"] == pytest.approx(v.peak_by["capacitive"], rel=0.05)


def test_a_victim_whose_ends_share_a_part_has_no_ground_difference():
    snap = buck_board(victim_gap=0.2)
    from kipi_si.dc.pi.model import PinRef
    v = Victim("SIG", driver=PinRef("U3", "SIG", ["1"]), receiver=PinRef("U3", "SIG", ["1"]))
    r = solve_noise(snap, _setup(snap, [v]), "U1 buck").victims[0]
    assert "common" not in r.peak_by


def test_a_board_model_that_cannot_be_built_falls_back():
    snap = buck_board()
    setup = _setup(snap, [])
    setup.aggressors[0].phases[0].inductor = ""             # no inductor pad to inject at
    setup.aggressors[0].phases[0].inductance_h = 1e-6
    r = solve_noise(snap, setup, "U1 buck")
    assert any("Board model left out" in w for w in r.warnings)
    assert r.board_note == "" and r.waveforms.input_caps


def _field_solves(result) -> int:
    import re
    return int(re.search(r"(\d+) field solves", " ".join(result.summary_lines())).group(1))


def test_the_board_model_solves_the_harmonics_its_interpolation_misses(monkeypatch):
    """Where the copper's response between the solved frequencies is not what they
    interpolate to, it is solved at the harmonics themselves (as AC mode's sweep)."""
    from kipi_si.ac.solver import sweep
    real, seen = sweep.refine_field, {}

    def spy(solve, f_field, zb, freqs, **kw):
        kw.pop("tol", None)
        f2, z2, why = real(solve, f_field, zb, freqs, tol=seen["tol"], max_extra=3, **kw)
        seen.update(base=np.array(f_field), freqs=np.array(freqs), out=f2, why=why)
        return f2, z2, why
    monkeypatch.setattr(sweep, "refine_field", spy)
    snap = buck_board()
    seen["tol"] = sweep.FIELD_TOL
    plain = solve_noise(snap, _setup(snap, []), "U1 buck")
    assert np.allclose(seen["freqs"], 1e6 * np.arange(1, len(seen["freqs"]) + 1))   # harmonics
    assert len(seen["out"]) == len(seen["base"]) == _field_solves(plain)   # smooth: no more
    seen["tol"] = 0.0                                   # nothing holds: up to the budget
    forced = solve_noise(snap, _setup(snap, []), "U1 buck")
    added = np.setdiff1d(seen["out"], seen["base"])
    assert len(added) == 3 and np.isin(added, seen["freqs"]).all()
    assert _field_solves(forced) == len(seen["base"]) + 3
    assert any("3 more frequencies" in w for w in forced.warnings)
    # Solved at more points of a smooth response, the answer is the same.
    a, b = plain.waveforms.input_ripple.c, forced.waveforms.input_ripple.c
    assert np.allclose(a, b, rtol=0.02, atol=1e-3 * np.abs(a).max())


def test_the_board_model_keeps_to_its_solves_with_adaptive_off(monkeypatch):
    from kipi_si.ac.solver import sweep
    called = []
    monkeypatch.setattr(sweep, "refine_field", lambda *a, **k: called.append(1))
    snap = buck_board()
    setup = _setup(snap, [])
    setup.ac.field_adaptive = False
    solve_noise(snap, setup, "U1 buck")
    assert not called
