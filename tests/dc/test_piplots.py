"""The PI plots of a DC solve: loads against tolerance and the drop budget."""

import os
from types import SimpleNamespace

import pytest

from kipi_si.dc.pi import piplots
from kipi_si.dc.pi.model import PinRef
from kipi_si.dc.pi.tree import solve_tree
from kipi_si.si.siplots import Ink
from phase_boards import board, two_phase

INK = Ink(("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"), "#333", "#888")


@pytest.fixture(scope="module")
def solved():
    setup = two_phase(ground=True)
    setup.loads[0].tol_min, setup.loads[0].tol_max = -0.5, 0.5     # ±0.5 % of 1 V
    return solve_tree(board(), setup), setup


def test_load_margins_carry_the_solve_and_its_verdict(solved):
    tree, _ = solved
    (row,) = piplots.load_margins(tree)
    rep = tree.loads[0]
    assert (row.name, row.nominal, row.v_mean) == ("U2", 1.0, rep.v_effective)
    assert row.limit_low == pytest.approx(0.995) and row.limit_high == pytest.approx(1.005)
    assert row.status == ("PASS" if rep.passed else "FAIL")
    assert row.pct(row.limit_low) == pytest.approx(-0.5)


def test_drop_budget_adds_up_to_the_drop(solved):
    tree, setup = solved
    (row,) = piplots.drop_budget(tree, setup)
    assert row.total == pytest.approx(tree.loads[0].drop, abs=1e-12)
    assert row.parts["Ground return"] == pytest.approx(tree.loads[0].v_ground)
    assert row.parts["Series parts"] == 0.0 and row.parts["Copper"] > 0


def test_series_parts_on_the_path_only():
    links = [SimpleNamespace(name=n, side_a=PinRef(n, a), side_b=PinRef(n, b))
             for n, a, b in (("FB1", "+5V", "VA"), ("R1", "VA", "VB"), ("R9", "+5V", "VC"))]
    assert [k.name for k in piplots._path_links("+5V", "VB", links)] == ["FB1", "R1"]
    assert piplots._path_links("+5V", "+5V", links) == []
    assert piplots._path_links("+5V", "NOPE", links) is None


def test_every_plot_draws(solved):
    pytest.importorskip("matplotlib")
    from matplotlib.figure import Figure
    tree, setup = solved
    for draw, rows in ((piplots.draw_loads, piplots.load_margins(tree)),
                       (piplots.draw_budget, piplots.drop_budget(tree, setup))):
        fig = Figure()
        draw(fig, rows, INK)
        assert fig.axes


def test_tab_shows_each_view(solved):
    pytest.importorskip("qtpy")
    pytest.importorskip("matplotlib")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from qtpy.QtWidgets import QApplication
    from kipi_si.dc.gui.pi_plot import VIEWS, PIPlot
    QApplication.instance() or QApplication([])
    tree, setup = solved
    w = PIPlot()
    w.set_result(tree, setup)
    texts = {}
    for key, _ in VIEWS:
        w.set_view(key)
        texts[key] = w.lbl.text()
        assert w.figure.axes
    assert "of 1 loads pass" in texts["loads"] or "fail" in texts["loads"]
    w.clear()
    assert w.tree is None
    w.close()
