"""The 3D view follows the windows' dark or light theme: its background, the text of its
color bars and axes, and the board's outline."""

from types import SimpleNamespace as NS

import pytest

pv = pytest.importorskip("pyvista")
pytest.importorskip("pyvistaqt")

from kipi_si.gui import viewer3d  # noqa: E402
from kipi_si.gui.viewer3d import SCHEMES, Viewer3D, _bar_args, _bar_title_actor  # noqa: E402


def _view():
    p = pv.Plotter(off_screen=True)
    p.add_axes()
    p.add_mesh(pv.Line(), color=SCHEMES[True]["outline"], name="outline")
    p.add_mesh(pv.Sphere(), scalars=range(pv.Sphere().n_points),
               scalar_bar_args=_bar_args("V (V)", "%.3f"))
    return NS(plotter=p, _dark=None, _bar_titles=[_bar_title_actor("V (V)")],
              _coupling_title=None, _field_title=None)


def _close(a, b):
    return all(abs(x - y) < 1e-3 for x, y in zip(a, b))


def test_light_theme_lightens_the_view_and_darkens_its_text():
    v = _view()
    try:
        Viewer3D.apply_theme(v, False)
        light = SCHEMES[False]
        p = v.plotter
        assert _close(p.background_color, pv.Color(light["background"][0]).float_rgb)
        bar = p.scalar_bars["V (V)"]
        assert _close(bar.GetLabelTextProperty().GetColor(), light["text"])
        assert _close(v._bar_titles[0].GetTextProperty().GetColor(), light["text"])
        cap = p.renderer.axes_actor.GetXAxisCaptionActor2D().GetCaptionTextProperty()
        assert _close(cap.GetColor(), light["text"])
        assert _close(p.actors["outline"].prop.color.float_rgb,
                      pv.Color(light["outline"]).float_rgb)
        # What is drawn after the switch takes the light scheme too.
        assert _bar_args("x", "%g")["color"] == light["text"]
        assert _close(_bar_title_actor("x").GetTextProperty().GetColor(), light["text"])

        Viewer3D.apply_theme(v, True)                        # and back
        dark = SCHEMES[True]
        assert _close(p.background_color, pv.Color(dark["background"][0]).float_rgb)
        assert _close(bar.GetLabelTextProperty().GetColor(), dark["text"])
    finally:
        viewer3d._scheme = SCHEMES[True]
        v.plotter.close()
