"""The Altium reader (``.PcbDoc``, ``.PrjPcb``).

``tests/data/altium/features.PcbDoc`` is written by ``make_fixtures.py`` with altium-monkey,
the reader's own package: one of each thing on a 2-layer board, in round mils, so the
expected values are worked out by hand (1 mil = 0.0254 mm; the file is y up about the
origin, the board y down). The tests that read it need altium-monkey (Python 3.12+); the
rest do not.

Set ``KIPI_SI_ALTIUM_BOARD`` to a real ``.PcbDoc`` to also read a full board and its
embedded 3D models (checked on the Pi.MX8 boards: 10 layers, blind and buried vias).
"""

import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest

from kipi_si.core.geometry.copper import poly_to_shapely
from kipi_si.core.model.layers import B_CU, F_CU
from kipi_si.sources import registry
from kipi_si.sources.altium import AltiumUnavailable, require
from kipi_si.sources.altium.models3d import body_transform
from kipi_si.sources.altium.project import project_boards
from kipi_si.sources.altium.reader import (
    BOTTOM, PLANE_1, TOP, legacy_layer, pad_shape, vertex_ring,
)

DATA = Path(__file__).parents[1] / "data" / "altium"
FEATURES = DATA / "features.PcbDoc"
MIL = 0.0254

needs_reader = pytest.mark.skipif(
    sys.version_info < (3, 12) or __import__("importlib").util.find_spec("altium_monkey") is None,
    reason="altium-monkey is not installed (it needs Python 3.12+)")


# --- without the reader ------------------------------------------------------------

def test_layer_ids():
    assert legacy_layer(0x01000001) == TOP
    assert legacy_layer(0x01000002) == 2               # Mid1
    assert legacy_layer(0x0100FFFF) == BOTTOM
    assert legacy_layer(0x01010003) == PLANE_1 + 2     # Internal Plane 3
    assert legacy_layer(0x01030007) is None            # an overlay


def test_arc_vertex_runs_from_the_end_it_is_nearer():
    """A vertex on an arc's start runs it counterclockwise; on its end, backwards."""
    ccw = vertex_ring([(1, 0, True, 0, 0, 1, 0, 90)])
    cw = vertex_ring([(0, 1, True, 0, 0, 1, 0, 90)])
    assert ccw[0] == pytest.approx((1, 0)) and ccw[-1] == pytest.approx((0, 1))
    assert cw[0] == pytest.approx((0, 1)) and cw[-1] == pytest.approx((1, 0))


def test_pad_shapes():
    assert pad_shape(1, 2, 2).area == pytest.approx(math.pi, rel=0.02)          # circle
    oval = pad_shape(1, 4, 2)
    assert oval.area == pytest.approx(2 * 2 + math.pi, rel=0.02)
    assert pad_shape(3, 4, 4).area == pytest.approx(16 - 4 * 0.5, rel=1e-9)      # octagon
    rr = pad_shape(2, 4, 2, corner_mm=0.5)
    assert rr.area == pytest.approx(8 - (4 - math.pi) * 0.25, rel=0.01)
    assert pad_shape(2, 0, 2) is None


def test_bottom_parts_turn_over_about_x():
    m, off = body_transform(0, 0, 0, 0.0, 0, 10.0, 20.0, bottom=True)
    p = m @ np.array([1.0, 2.0, 3.0]) + off
    assert p == pytest.approx([11.0, 18.0, -3.0])
    m, off = body_transform(0, 0, 90, 0.5, 0, 0, 0, bottom=False)
    assert m @ np.array([1.0, 0, 0]) + off == pytest.approx([0, 1.0, 0.5])


def test_project_lists_its_boards(tmp_path):
    (tmp_path / "PCB").mkdir()
    (tmp_path / "PCB" / "Main.PcbDoc").write_bytes(b"")
    (tmp_path / "PCB" / "Panel.PcbDoc").write_bytes(b"")
    prj = tmp_path / "board.PrjPcb"
    prj.write_text("\ufeff[Design]\nVersion=1.0\n"
                   "[Document1]\nDocumentPath=SCH\\top.SchDoc\n"
                   "[Document2]\nDocumentPath=PCB\\main.PcbDoc\n"     # case differs on disk
                   "[Document3]\nDocumentPath=PCB\\Panel.PcbDoc\n"
                   "[Document4]\nDocumentPath=PCB\\Gone.PcbDoc\n"
                   "[Configuration1]\nDocumentPath=C:\\elsewhere\\Other.PcbDoc\n",
                   encoding="utf-8")
    assert project_boards(prj) == [tmp_path / "PCB" / "Main.PcbDoc",
                                   tmp_path / "PCB" / "Panel.PcbDoc"]
    assert registry.boards_in(prj) == project_boards(prj)
    assert registry.boards_in(FEATURES) == []


def test_open_dialog_offers_altium():
    assert registry.format_for("x.PcbDoc").name == "Altium Designer"
    assert registry.format_for("x.PRJPCB").name == "Altium Designer"
    assert "*.PcbDoc" in registry.file_filter()      # as Altium names them


def test_without_the_reader_it_says_how_to_get_it(monkeypatch):
    import kipi_si.sources.altium as altium
    monkeypatch.setitem(sys.modules, "altium_monkey", None)       # import fails
    # Too old a Python is said first, whatever this one is ...
    monkeypatch.setattr(altium, "MIN_PYTHON", (99, 0))
    with pytest.raises(AltiumUnavailable, match="needs Python 99.0 or newer"):
        require()
    # ... and on a new enough one, how to install the reader.
    monkeypatch.setattr(altium, "MIN_PYTHON", (3, 0))
    with pytest.raises(AltiumUnavailable, match="--add-altium"):
        require()
    monkeypatch.setattr(altium, "MIN_PYTHON", (3, 12))
    if sys.version_info >= (3, 12):
        with pytest.raises(ValueError, match="altium-monkey"):
            registry.open_board(FEATURES)


# --- with the reader ---------------------------------------------------------------

@pytest.fixture(scope="module")
def snap():
    from kipi_si.sources.altium.reader import read_board
    return read_board(FEATURES)


def _area(polys) -> float:
    return sum(poly_to_shapely(p).area for p in polys)


@needs_reader
def test_identity_and_stackup(snap):
    assert snap.board_name == "features.PcbDoc" and snap.source_format == "altium"
    assert snap.format_name == "Altium Designer"
    st = snap.stackup
    assert [c.id for c in st.copper] == [F_CU, B_CU]
    assert [c.name for c in st.copper] == ["Top Layer", "Bottom Layer"]
    assert st.from_board and len(st.dielectrics) == 1
    assert st.dielectrics[0].material and st.dielectrics[0].epsilon_r > 1
    assert {(c.kind, c.side) for c in st.coatings} == {
        ("mask", "top"), ("mask", "bottom"), ("silk", "top"), ("silk", "bottom")}


@needs_reader
def test_outline(snap):
    (board,) = snap.outline
    g = poly_to_shapely(board)
    assert g.bounds == pytest.approx((0, -1000 * MIL, 2000 * MIL, 0), abs=1e-6)


@needs_reader
def test_pads(snap):
    smd = next(p for p in snap.pads if p.number == "1")
    assert smd.pad_type == "smd" and smd.net == "VCC"
    assert smd.position == pytest.approx((450 * MIL, -500 * MIL))
    assert list(smd.shapes) == [F_CU]
    # 40 x 60 mil with corners rounded by 50 % of half its shorter side: r = 10 mil.
    r = 10 * MIL
    assert _area(smd.shapes[F_CU]) == pytest.approx(
        40 * 60 * MIL ** 2 - (4 - math.pi) * r * r, rel=0.01)
    th = next(p for p in snap.pads if p.number == "2")
    assert th.pad_type == "pth" and th.net == "GND"
    assert sorted(th.shapes) == [F_CU, B_CU]
    assert th.drill_mm == pytest.approx((30 * MIL, 30 * MIL))


@needs_reader
def test_part(snap):
    (u1,) = snap.footprints
    assert u1.reference == "U1" and u1.footprint == "TEST_PKG" and u1.side == "top"
    assert u1.angle_deg == pytest.approx(90.0)
    assert u1.position == pytest.approx((500 * MIL, -500 * MIL))
    assert u1.fields["MPN"] == "ABC-123"


@needs_reader
def test_via_and_tracks(snap):
    (via,) = snap.vias
    assert via.via_type == "through" and via.layers == [F_CU, B_CU] and via.net == "VCC"
    assert via.drill_mm == pytest.approx(12 * MIL) and via.diameter_mm == pytest.approx(24 * MIL)
    straight = [t for t in snap.tracks if not t.is_arc]
    assert {(t.layer, t.net) for t in straight} == {(F_CU, "VCC"), (B_CU, "VCC")}
    (arc,) = [t for t in snap.tracks if t.is_arc]
    # About (1000, 300) mil, r = 100, from 0 to 90 degrees counterclockwise (y up).
    assert arc.start == pytest.approx((1100 * MIL, -300 * MIL))
    assert arc.end == pytest.approx((1000 * MIL, -400 * MIL))
    c = 100 * MIL / math.sqrt(2)
    assert arc.mid == pytest.approx((1000 * MIL + c, -300 * MIL - c), abs=1e-5)


@needs_reader
def test_copper_areas(snap):
    by_layer = {lid: polys for z in snap.zones if z.net == "GND"
                for lid, polys in z.filled.items()}
    assert _area(by_layer[F_CU]) == pytest.approx(200 * 200 * MIL ** 2)       # the fill
    assert _area(by_layer[B_CU]) == pytest.approx(300 * 200 * MIL ** 2)       # the region
    assert {n.name for n in snap.nets} == {"", "VCC", "GND"}


@needs_reader
def test_source_reads_a_project(tmp_path):
    import shutil
    (tmp_path / "PCB").mkdir()
    shutil.copy(FEATURES, tmp_path / "PCB" / "features.PcbDoc")
    prj = tmp_path / "p.PrjPcb"
    prj.write_text("[Document1]\nDocumentPath=PCB\\features.PcbDoc\n")
    source = registry.open_board(prj)
    assert source.files() == [tmp_path / "PCB" / "features.PcbDoc"]
    assert source.has_part_models and source.caps.reload
    assert source.load().board_name == "features.PcbDoc"


@needs_reader
def test_parts_without_embedded_models_have_none(snap):
    from kipi_si.sources.altium.models3d import EmbeddedModels
    assert EmbeddedModels(FEATURES, 1.6).load(["U1", "NOPE"]) == {"U1": None, "NOPE": None}


# --- a real board, when one is given ------------------------------------------------

REAL = os.environ.get("KIPI_SI_ALTIUM_BOARD", "")


@needs_reader
@pytest.mark.skipif(not REAL or not Path(REAL).is_file(),
                    reason="set KIPI_SI_ALTIUM_BOARD to a .PcbDoc to read a real board")
@pytest.mark.timeout(600)
def test_real_board_and_its_models():
    from kipi_si.sources.altium.models3d import EmbeddedModels
    from kipi_si.sources.altium.reader import read_board
    snap = read_board(REAL)
    assert snap.stackup.from_board and len(snap.stackup.copper) >= 2
    assert snap.outline and snap.pads and snap.footprints and snap.tracks
    on_parts = sum(1 for p in snap.pads if p.footprint)
    assert on_parts > 0.9 * len(snap.pads)
    known = {n.name for n in snap.nets}
    assert all(p.net in known for p in snap.pads) and all(v.net in known for v in snap.vias)
    # Every via and pad lies on the board.
    import shapely
    board = shapely.union_all([poly_to_shapely(p) for p in snap.outline]).buffer(0.01)
    assert all(board.contains(shapely.Point(v.position)) for v in snap.vias)
    # Some parts have a model, and each sits on its side of the board.
    t = snap.stackup.board_thickness_mm
    side = {f.reference: f.side for f in snap.footprints}
    refs = [f.reference for f in snap.footprints][:20]
    models = EmbeddedModels(REAL, t).load(refs)
    shown = {r: m for r, m in models.items() if m is not None}
    assert shown
    for r, m in shown.items():
        zmin, zmax = m.bounds[4], m.bounds[5]
        if side[r] == "top":
            assert zmin >= t - 0.05
        else:
            assert zmax <= 0.05
