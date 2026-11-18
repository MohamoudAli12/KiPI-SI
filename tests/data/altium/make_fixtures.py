"""Write ``features.PcbDoc``, a small Altium board for tests/sources/test_altium_reader.py.

    uv run python tests/data/altium/make_fixtures.py

It is authored with altium-monkey (the reader's own package): a 60 x 40 mil-grid board
with an outline, two nets, tracks and an arc on both sides, a through via, a rounded SMD
pad and a plated through-hole pad on a part, a copper region and a fill. Coordinates are
in mils about Altium's origin.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def build(out: Path) -> Path:
    from altium_monkey import AltiumPcbDoc, PadShape, PcbDocBuilder, PcbLayer
    tmp = out.with_suffix(".blank.PcbDoc")
    PcbDocBuilder().save(tmp)
    doc = AltiumPcbDoc.from_file(tmp)
    tmp.unlink()
    doc.set_outline_rectangle_mils(0, 0, 2000, 1000)
    doc.set_origin_mils(0, 0) if hasattr(doc, "set_origin_mils") else None
    for net in ("VCC", "GND"):
        doc.add_net(net)
    doc.add_component(designator="U1", footprint="TEST_PKG", position_mils=(500, 500),
                      layer="TOP", rotation_degrees=90.0, description="Test part",
                      parameters={"MPN": "ABC-123"})
    doc.add_pad(designator="1", position_mils=(450, 500), width_mils=40, height_mils=60,
                layer=PcbLayer.TOP, shape=PadShape.ROUNDED_RECTANGLE, corner_radius_percent=50,
                net="VCC")
    doc.add_pad(designator="2", position_mils=(550, 500), width_mils=60, height_mils=60,
                layer=PcbLayer.MULTI_LAYER, shape=PadShape.CIRCLE, hole_size_mils=30,
                plated=True, net="GND")
    doc.add_track((450, 500), (1500, 500), width_mils=20, layer=PcbLayer.TOP, net="VCC")
    doc.add_track((1500, 500), (1500, 800), width_mils=20, layer=PcbLayer.BOTTOM, net="VCC")
    doc.add_arc(center_mils=(1000, 300), radius_mils=100, start_angle_degrees=0,
                end_angle_degrees=90, width_mils=10, layer=PcbLayer.TOP, net="GND")
    doc.add_via(position_mils=(1500, 500), diameter_mils=24, hole_size_mils=12, net="VCC")
    doc.add_region(outline_points_mils=[(100, 100), (400, 100), (400, 300), (100, 300)],
                   layer=PcbLayer.BOTTOM, net="GND")
    doc.add_fill((1700, 100), (1900, 300), layer=PcbLayer.TOP, net="GND")
    doc.save(out)
    return out


if __name__ == "__main__":
    print(build(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "features.PcbDoc"))
