"""The plots beside the 3D view follow the windows' dark or light theme: a switch redraws
them, empty or showing a result, in the new theme's colours."""

import os

import pytest

pytest.importorskip("qtpy")
pytest.importorskip("matplotlib")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from matplotlib.colors import to_hex  # noqa: E402
from qtpy.QtWidgets import QApplication  # noqa: E402

from kipi_si.gui import plot_theme, theme  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def dark_after(app):
    # theme.apply only, never theme.choose: the user's saved choice is left alone.
    yield app
    theme.apply(theme.DARK, app)
    app.processEvents()


def _plots():
    from kipi_si.ac.gui.board_map import BoardMap
    from kipi_si.ac.gui.plot import ImpedancePlot
    from kipi_si.ac.gui.transient_plot import TransientPlot
    from kipi_si.dc.gui.pi_plot import PIPlot
    from kipi_si.noise.gui.plot import NoisePlot
    from kipi_si.si.gui.plot import SIPlot
    return [PIPlot(), SIPlot(), ImpedancePlot(), TransientPlot(), BoardMap(), NoisePlot()]


def _faces(plot):
    return ({to_hex(plot.figure.get_facecolor())}
            | {to_hex(ax.get_facecolor()) for ax in plot.figure.axes})


def test_every_plot_redraws_in_the_theme_switched_to(dark_after):
    app = dark_after
    theme.apply(theme.DARK, app)
    plots = _plots()
    for p in plots:
        assert _faces(p) == {plot_theme.DARK.bg}, type(p).__name__
    theme.apply(theme.LIGHT, app)
    app.processEvents()
    for p in plots:
        assert _faces(p) == {plot_theme.LIGHT.bg}, type(p).__name__
        ax = p.figure.axes[0]
        assert to_hex(ax.xaxis.label.get_color()) == plot_theme.LIGHT.fg
    assert plot_theme.SERIES == list(plot_theme.LIGHT.series)
    theme.apply(theme.DARK, app)
    app.processEvents()
    for p in plots:
        assert _faces(p) == {plot_theme.DARK.bg}, type(p).__name__
        p.close()
    assert plot_theme.SERIES == list(plot_theme.DARK.series)


def test_a_shown_result_is_drawn_again_in_the_new_theme(dark_after):
    from phase_boards import board, two_phase

    from kipi_si.dc.gui.pi_plot import PIPlot
    from kipi_si.dc.pi.tree import solve_tree
    app = dark_after
    theme.apply(theme.DARK, app)
    p = PIPlot()
    p.set_result(solve_tree(board(), two_phase()))
    assert p.tree is not None
    theme.apply(theme.LIGHT, app)
    app.processEvents()
    assert p.tree is not None                      # the result is kept, not cleared
    assert _faces(p) == {plot_theme.LIGHT.bg}
    p.close()


def test_plots_made_while_light_start_light(dark_after):
    from kipi_si.ac.gui.plot import ImpedancePlot
    app = dark_after
    theme.apply(theme.LIGHT, app)
    p = ImpedancePlot()
    assert _faces(p) == {plot_theme.LIGHT.bg}
    p.close()
