"""The analysis panels' last tab, Solve: the Solve button and the results there, after
the tabs that set the problem up; why an Add button added nothing shown under the tabs."""

import os

import pytest

pytest.importorskip("qtpy")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qtpy.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _panels():
    from kipi_si.ac.gui.panel import ACPanel
    from kipi_si.dc.gui.pi_panel import PIPanel
    from kipi_si.noise.gui.panel import NoisePanel
    from kipi_si.si.gui.panel import SIPanel
    return [PIPanel(), ACPanel(), NoisePanel(), SIPanel()]


def test_solve_is_the_last_tab_and_holds_the_button_and_results(app):
    for p in _panels():
        tabs = p.tabs
        assert tabs.tabText(tabs.count() - 1) == "Solve", type(p).__name__
        assert tabs.widget(tabs.count() - 1) is p.solve_page
        for w in (p.btn_solve, p.lbl_errors, p.txt_notes):
            assert p.solve_page.isAncestorOf(w), (type(p).__name__, w)
        assert not p.solve_page.isAncestorOf(p.lbl_notice)
        p.close()


def test_dc_tab_order(app):
    from kipi_si.dc.gui.pi_panel import PIPanel
    p = PIPanel()
    assert [p.tabs.tabText(i) for i in range(p.tabs.count())] == [
        "VRMs", "Loads", "Series links", "Mesh", "Thermal", "Solve"]
    p.close()


def test_si_tab_order(app):
    from kipi_si.si.gui.panel import SIPanel
    p = SIPanel()
    assert [p.tabs.tabText(i) for i in range(p.tabs.count())] == [
        "Quick Scan", "Channels", "Settings", "Solve"]
    p.close()


def test_the_solve_tab_is_flagged_while_the_solve_cannot_run(app):
    from kipi_si.dc.gui.pi_panel import PIPanel
    p = PIPanel()
    i = p.tabs.indexOf(p.solve_page)
    p.flag_solve_tab(["Add a VRM"])
    assert "Add a VRM" in p.tabs.tabToolTip(i)
    assert p.tabs.tabBar().tabTextColor(i).name() == "#ff8080"
    p.flag_solve_tab([])
    assert "Add a VRM" not in p.tabs.tabToolTip(i)
    p.close()


def test_an_error_or_results_bring_the_solve_tab_forward(app):
    for p in _panels():
        p.tabs.setCurrentIndex(0)
        p.show_error("no copper")
        assert p.tabs.currentWidget() is p.solve_page, type(p).__name__
        p.close()


def test_add_notice_is_seen_from_the_setup_tabs_and_clears_on_a_tab_switch(app):
    from kipi_si.dc.gui.pi_panel import PIPanel
    p = PIPanel()
    p.show()
    p.tabs.setCurrentWidget(p.vrm_list)
    p.notice("• No net is ticked")
    assert p.lbl_notice.isVisible() and "No net" in p.lbl_notice.text()
    p.tabs.setCurrentWidget(p.load_list)
    assert not p.lbl_notice.isVisible()
    p.close()
