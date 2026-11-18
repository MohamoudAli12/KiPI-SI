"""Read an Altium Designer board (``.PcbDoc``) into a
:class:`~kipi_si.core.model.board.BoardSnapshot`, with the optional ``altium-monkey`` package.

What is read: the layer stack (copper, dielectrics with their materials, solder masks and
overlays), every net and part, the pads (their shape on each copper layer, the removed
unused lands, custom pad shapes), the vias (blind and buried, with their per-layer pads),
tracks and arcs, fills, copper regions and the poured copper of each polygon as Altium
last poured it, the internal planes, the board outline with its cutouts, and the
overlays' graphics as the silkscreen.

Altium's coordinates are y up, in internal units of 1/10000 mil, about the board's
absolute origin. KiPI-SI's board is in mm, y down, about the board's origin as Altium
shows it: the file's (x, y) is ((x - ox), -(y - oy)). Geometry is built in the file's
y-up frame (in mm) and turned into the board's frame last (:func:`_board_geom`).

Altium's layers are numbered Top = 1, Mid1..Mid30 = 2..31, Bottom = 32, the overlays
33 / 34 and the internal planes 39..54; KiPI-SI numbers the copper by its place in the stack
(:func:`~kipi_si.core.model.layers.copper_id`).
"""

from __future__ import annotations

import math
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from kipi_si.core.geometry.copper import shapely_to_polys
from kipi_si.core.geometry import silkscreen as silk
from kipi_si.core.model.board import (
    BoardSnapshot, Footprint, Net, Pad, Poly, Track, Via, Zone,
)
from kipi_si.core.model.layers import copper_id
from kipi_si.core.model.stackup import (
    DEFAULT_INNER_CU_MM, DEFAULT_OUTER_CU_MM, build_stackup, coating_of,
)
from kipi_si.core.progress import NULL, ProgressReporter

MM_PER_MIL = 0.0254
MM_PER_UNIT = MM_PER_MIL / 10000.0       # Altium's internal unit: 1/10000 mil
NM = 6                                   # decimals of a mm kept: 1 nm
QUAD_SEGS = 8                            # segments in a quarter circle
NO_INDEX = 65535                         # "none" for a net, polygon or component index

# Legacy layer ids.
TOP, BOTTOM = 1, 32
TOP_OVERLAY, BOTTOM_OVERLAY = 33, 34
PLANE_1, PLANE_16 = 39, 54
MULTI_LAYER = 74
# V7 saved layer ids, as the stack lists its layers.
_V7_SIGNAL = 0x01000000
_V7_PLANE = 0x01010000
_V7_FAMILY = 0xFFFF0000

# Pad shapes, and the hole shapes.
CIRCLE, RECTANGLE, OCTAGONAL, ROUNDED_RECTANGLE = 1, 2, 3, 4
HOLE_SLOT = 2
# Region kinds (altium-monkey's semantic ones).
REGION_COPPER, REGION_BOARD_CUTOUT = 0, 1
# Dielectric types in the stack: 3 is a surface layer (solder mask, coverlay).
DIEL_SURFACE = 3
#: Altium's default pull-back of a plane from the board edge, used for every plane.
PLANE_PULLBACK_MM = 20 * MM_PER_MIL


class AltiumError(ValueError):
    pass


def is_copper(layer: int) -> bool:
    return TOP <= layer <= BOTTOM or PLANE_1 <= layer <= PLANE_16


def is_plane(layer: int) -> bool:
    return PLANE_1 <= layer <= PLANE_16


def legacy_layer(v7_id: int) -> Optional[int]:
    """The legacy id of a V7 saved layer id, for copper layers; None for any other."""
    family, low = v7_id & _V7_FAMILY, v7_id & 0xFFFF
    if family == _V7_SIGNAL:
        if low == 0xFFFF:
            return BOTTOM
        return low if 1 <= low <= 31 else None
    if family == _V7_PLANE and 1 <= low <= 16:
        return PLANE_1 + low - 1
    return None


def _mm(units) -> float:
    return float(units or 0) * MM_PER_UNIT


# ---------------------------------------------------------------------------
# Geometry in the file's frame (mm, y up)
# ---------------------------------------------------------------------------

class Frame:
    """The file's frame in mm (y up) to the board's (y down, about the origin)."""

    def __init__(self, ox_mm: float, oy_mm: float):
        self.ox, self.oy = ox_mm, oy_mm

    def pt(self, x_mm: float, y_mm: float) -> Tuple[float, float]:
        return (round(x_mm - self.ox, NM), round(-(y_mm - self.oy), NM))

    def units(self, x, y) -> Tuple[float, float]:
        return self.pt(_mm(x), _mm(y))

    def geom(self, g):
        from shapely import affinity
        return affinity.affine_transform(g, [1, 0, 0, -1, -self.ox, self.oy])


def arc_points(cx, cy, r, a0_deg, a1_deg, reverse: bool = False) -> List[Tuple[float, float]]:
    """The arc about (cx, cy) counterclockwise (y up) from ``a0_deg`` to ``a1_deg``; the
    same angle twice is a full circle. ``reverse`` gives it end first."""
    sweep = (a1_deg - a0_deg) % 360.0
    if sweep < 1e-9:
        sweep = 360.0
    n = max(2, int(math.ceil(sweep / 90.0 * QUAD_SEGS)))
    a0 = math.radians(a0_deg)
    s = math.radians(sweep)
    pts = [(cx + r * math.cos(a0 + s * i / n), cy + r * math.sin(a0 + s * i / n))
           for i in range(n + 1)]
    return pts[::-1] if reverse else pts


def vertex_ring(vertices: Iterable[tuple]) -> List[Tuple[float, float]]:
    """An outline from Altium's vertices, each ``(x, y, is_arc, cx, cy, r, a0, a1)`` in mm
    and degrees. An arc vertex is an arc about (cx, cy) from a0 to a1, counterclockwise,
    followed backwards when the vertex is nearer its end than its start (as KiCad's
    importer reads them)."""
    pts: List[Tuple[float, float]] = []
    for x, y, is_arc, cx, cy, r, a0, a1 in vertices:
        if is_arc and r > 0:
            start = (cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0)))
            end = (cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1)))
            forward = math.dist(start, (x, y)) <= math.dist(end, (x, y))
            pts.extend(arc_points(cx, cy, r, a0, a1, reverse=not forward))
        else:
            pts.append((x, y))
    out: List[Tuple[float, float]] = []
    for p in pts:
        if not out or math.dist(out[-1], p) > 1e-7:
            out.append(p)
    if len(out) > 1 and math.dist(out[0], out[-1]) <= 1e-7:
        out.pop()
    return out


def _ext_vertex(v) -> tuple:
    """A ShapeBasedRegions6 vertex (internal units) as a :func:`vertex_ring` tuple."""
    return (_mm(v.x), _mm(v.y), bool(getattr(v, "is_round", False)), _mm(v.center_x),
            _mm(v.center_y), _mm(v.radius), float(v.start_angle), float(v.end_angle))


def _simple_vertex(v) -> tuple:
    return (_mm(v.x), _mm(v.y), False, 0.0, 0.0, 0.0, 0.0, 0.0)


def region_geom(region):
    """A shape-based region's area in the file's frame (shapely), or None."""
    import shapely
    from shapely.geometry import Polygon
    ring = vertex_ring(_ext_vertex(v) for v in region.outline_vertices)
    if len(ring) < 3:
        return None
    holes = []
    for h in (getattr(region, "hole_vertices", None) or []):
        hr = vertex_ring(_simple_vertex(v) if not hasattr(v, "center_x") else _ext_vertex(v)
                         for v in h)
        if len(hr) >= 3:
            holes.append(hr)
    g = Polygon(ring, holes)
    if not g.is_valid:
        g = shapely.make_valid(Polygon(ring))
        if holes:
            g = g.difference(shapely.union_all([shapely.make_valid(Polygon(h)) for h in holes]))
    return g


def stroke(points: Sequence[Tuple[float, float]], width: float):
    """A track along ``points`` ``width`` wide, with round ends (shapely)."""
    from shapely.geometry import LineString, Point
    if width <= 0:
        return None
    if len(points) < 2 or all(math.dist(points[0], p) < 1e-9 for p in points[1:]):
        return Point(points[0]).buffer(width / 2, quad_segs=QUAD_SEGS)
    return LineString(points).buffer(width / 2, quad_segs=QUAD_SEGS)


def pad_shape(shape: int, w: float, h: float, corner_mm: float = 0.0):
    """A pad's copper about its centre, unturned (shapely), or None when it has no size.

    A round pad that is not square is an oval (round-ended along its longer side); an
    octagon has its corners cut by a quarter of its shorter side; a rectangle with a
    corner radius is a rounded rectangle."""
    from shapely.geometry import Point, Polygon, box
    if w <= 0 or h <= 0:
        return None
    if shape == CIRCLE:
        if abs(w - h) < 1e-9:
            return Point(0, 0).buffer(w / 2, quad_segs=QUAD_SEGS)
        r = min(w, h) / 2
        return box(-w / 2 + r, -h / 2 + r, w / 2 - r, h / 2 - r).buffer(r, quad_segs=QUAD_SEGS)
    if shape == OCTAGONAL:
        c = min(w, h) / 4
        x, y = w / 2, h / 2
        return Polygon([(-x + c, -y), (x - c, -y), (x, -y + c), (x, y - c), (x - c, y),
                        (-x + c, y), (-x, y - c), (-x, -y + c)])
    r = min(max(corner_mm, 0.0), min(w, h) / 2)
    if r > 1e-9:
        return box(-w / 2 + r, -h / 2 + r, w / 2 - r, h / 2 - r).buffer(r, quad_segs=QUAD_SEGS)
    return box(-w / 2, -h / 2, w / 2, h / 2)


# ---------------------------------------------------------------------------
# Stackup
# ---------------------------------------------------------------------------

class Stack:
    """The copper layers in stack order (legacy ids) and the snapshot's stackup."""

    def __init__(self, order: List[int], ids: Dict[int, int], stackup):
        self.order = order                  # legacy ids, top to bottom
        self.ids = ids                      # legacy id -> KiPI-SI id
        self.stackup = stackup


def read_stackup(board, progress: ProgressReporter, assumed: List[str]) -> Stack:
    """The layer stack, from the V9 stack (every layer in order, dielectrics included) or,
    for an older file, the legacy one (the copper linked top to bottom, each with the
    dielectric under it)."""
    rows = []          # ("cu", legacy, t_mm, name) / ("diel", t_mm, material, er, tand) / coatings
    coatings = []
    v9 = list(getattr(board, "v9_stack", None) or [])
    if v9:
        copper_at = [i for i, l in enumerate(v9) if legacy_layer(l.layer_id) is not None]
        first, last = (copper_at[0], copper_at[-1]) if copper_at else (len(v9), -1)
        for i, l in enumerate(v9):
            name = (l.name or "").strip()
            lid = legacy_layer(l.layer_id)
            if lid is not None:
                rows.append(("cu", lid, float(l.copper_thickness or 0) * MM_PER_MIL, name))
            elif first < i < last:
                if float(l.diel_height or 0) > 0 or l.diel_type:
                    rows.append(("diel", float(l.diel_height or 0) * MM_PER_MIL,
                                 (l.diel_material or "").strip(), float(l.diel_constant or 0),
                                 float(getattr(l, "diel_loss_tangent", 0) or 0)))
            else:
                prefix = "F." if i < first else "B."
                low = name.lower()
                if "solder" in low or (l.diel_type == DIEL_SURFACE and "paste" not in low):
                    coatings.append(coating_of(prefix, "Solder Mask",
                                               float(l.diel_height or 0) * MM_PER_MIL,
                                               (l.diel_material or "").strip()))
                elif "overlay" in low or "silk" in low:
                    coatings.append(coating_of(prefix, "Silk Screen"))
    else:
        by_id = {l.layer_id: l for l in (getattr(board, "layer_stackup", None) or [])}
        seen = set()
        lid = TOP
        while lid in by_id and lid not in seen:
            seen.add(lid)
            l = by_id[lid]
            rows.append(("cu", lid, float(l.copper_thickness or 0) * MM_PER_MIL, l.name or ""))
            nxt = l.layer_next
            if nxt in by_id and nxt not in seen:
                rows.append(("diel", float(l.diel_height or 0) * MM_PER_MIL,
                             (l.diel_material or "").strip(), float(l.diel_constant or 0), 0.0))
            lid = nxt
        coatings = [coating_of("F.", "Solder Mask"), coating_of("B.", "Solder Mask")]
        assumed.append("Stackup: the file has only Altium's legacy layer stack, so the solder "
                       "masks are given KiCad's default thickness")

    order = [r[1] for r in rows if r[0] == "cu"]
    if not order:
        raise AltiumError("the board has no copper layers in its layer stack")
    n = len(order)
    ids = {lid: copper_id(i, n) for i, lid in enumerate(order)}
    names = {ids[r[1]]: r[3] or f"Layer {r[1]}" for r in rows if r[0] == "cu"}

    entries = []
    missing_cu, missing_diel = [], []
    for r in rows:
        if r[0] == "cu":
            t = r[2]
            if t <= 0:
                missing_cu.append(names[ids[r[1]]])
                t = DEFAULT_OUTER_CU_MM if r[1] in (order[0], order[-1]) else DEFAULT_INNER_CU_MM
            entries.append(("cu", ids[r[1]], t, "", 0.0))
        else:
            _, t, mat, er, tand = r
            if t <= 0:
                missing_diel.append(mat or "a dielectric")
            entries.append(("diel", -1, t, mat, er, tand))
    if missing_diel:
        known = [e[2] for e in entries if e[0] == "diel" and e[2] > 0]
        fill = sum(known) / len(known) if known else 0.2
        entries = [e if e[0] == "cu" or e[2] > 0 else (e[0], e[1], fill) + tuple(e[3:])
                   for e in entries]
        assumed.append(f"Stackup: no thickness in the file for {', '.join(missing_diel)}, so "
                       f"{fill:.3f} mm is used for each (the mean of the other dielectrics)")
    if missing_cu:
        assumed.append(f"Stackup: no copper thickness in the file for {', '.join(missing_cu)}, "
                       "so 35 um outer / 17.5 um inner copper is used")
    if n > 1 and not any(e[0] == "diel" for e in entries):
        entries = []                     # no dielectrics at all: the default stackup
    stackup = build_stackup(entries, [ids[l] for l in order], names, progress, assumed,
                            [c for c in coatings if c is not None])
    return Stack(order, ids, stackup)


# ---------------------------------------------------------------------------
# The board
# ---------------------------------------------------------------------------

def open_doc(path):
    from kipi_si.sources.altium import require
    require()
    from altium_monkey import AltiumPcbDoc
    try:
        return AltiumPcbDoc.from_file(str(path))
    except Exception as e:  # noqa: BLE001 - any parse failure is the file's
        raise AltiumError(f"{Path(path).name} could not be read as an Altium board: {e}") from e


def read_board(path, progress: ProgressReporter = NULL, doc=None) -> BoardSnapshot:
    """Read the ``.PcbDoc`` at ``path`` (or the already-parsed ``doc``). Raises
    :class:`AltiumError` for a file KiPI-SI cannot read, and
    :class:`~kipi_si.sources.altium.AltiumUnavailable` without the reader package."""
    path = Path(path).resolve()
    t0 = time.perf_counter()
    if doc is None:
        with progress.timed("Reading the file"):
            doc = open_doc(path)
    try:
        from importlib.metadata import version
        progress.info(f"Altium PcbDoc, read with altium-monkey {version('altium-monkey')}")
    except Exception:  # noqa: BLE001
        pass
    progress.check_cancel()
    return _Reader(doc, path, progress).read(t0)


class _Reader:
    def __init__(self, doc, path: Path, progress: ProgressReporter):
        self.doc = doc
        self.path = path
        self.progress = progress
        self.assumed: List[str] = []
        board = doc.board
        self.frame = Frame(float(board.origin_x or 0) * MM_PER_MIL,
                           float(board.origin_y or 0) * MM_PER_MIL)
        self.net_names = [(n.name or "").strip() for n in doc.nets]

    def net(self, index) -> str:
        if index is None or index == NO_INDEX or not 0 <= int(index) < len(self.net_names):
            return ""
        return self.net_names[int(index)]

    def read(self, t0: float) -> BoardSnapshot:
        p = self.progress
        with p.timed("Reading stackup"):
            self.stack = read_stackup(self.doc.board, p, self.assumed)
        st = self.stack
        self.copper = set(st.order)
        # Copper by net and layer, for the zones: key -> (net, name, {layer: [geoms]}).
        self.areas: Dict[str, Tuple[str, str, Dict[int, list]]] = {}

        with p.timed("Reading parts and pads"):
            footprints, pads = self._parts_and_pads()
        p.info(f"{len(footprints)} footprints, {len(pads)} pads")
        p.check_cancel()
        with p.timed("Reading vias"):
            vias = self._vias()
        p.info(f"{len(vias)} vias")
        with p.timed("Reading tracks"):
            tracks, split_lines = self._tracks()
        p.info(f"{len(tracks)} track segments ({sum(t.is_arc for t in tracks)} arcs)")
        p.check_cancel()
        with p.timed("Reading copper areas"):
            self._fills()
            self._regions()
        with p.timed("Reading board outline"):
            outline_g = self._outline()
        if any(is_plane(l) for l in st.order):
            with p.timed("Making the planes"):
                self._planes(outline_g, pads, vias, split_lines)
        zones = self._zones()
        p.info(f"{len(zones)} copper areas")
        with p.timed("Reading silkscreen"):
            silkscreen = self._silkscreen()

        names = set(self.net_names) | {""}
        classes = self._net_classes()
        nets = [Net(code=i, name=n, netclass=classes.get(n, ""))
                for i, n in enumerate(sorted(names))]
        snap = BoardSnapshot(
            board_name=self.path.name, project_dir=str(self.path.parent), stackup=st.stackup,
            nets=nets, tracks=tracks, vias=vias, pads=pads, footprints=footprints, zones=zones,
            outline=shapely_to_polys(self.frame.geom(outline_g)) if outline_g is not None else [],
            source="altium", source_format="altium", assumed=self.assumed,
            silkscreen=silkscreen)
        p.info(f"{len(nets)} nets")
        p.info(f"Read in {time.perf_counter() - t0:.2f} s")
        return snap

    # ----------------------------------------------------------------- parts
    def _parts_and_pads(self) -> Tuple[List[Footprint], List[Pad]]:
        doc = self.doc
        comments: Dict[int, str] = {}
        for t in doc.texts:
            if getattr(t, "is_comment", False) and t.component_index is not None:
                text = getattr(t, "text_content", "") or ""
                comments.setdefault(int(t.component_index), str(text).strip())
        footprints: List[Footprint] = []
        by_index: Dict[int, Footprint] = {}
        for i, c in enumerate(doc.components):
            ref = (c.designator or "").strip()
            fields = {str(k): str(v) for k, v in (c.parameters or {}).items()}
            value = comments.get(i, "")
            if value:
                fields.setdefault("Comment", value)
            if c.description:
                fields.setdefault("Description", str(c.description))
            fp = Footprint(
                id=str(c.unique_id or ref or f"component{i}"), reference=ref, value=value,
                position=self.frame.pt(c.get_x_mils() * MM_PER_MIL, c.get_y_mils() * MM_PER_MIL),
                side="bottom" if str(c.layer).upper() == "BOTTOM" else "top",
                footprint=str(c.footprint or ""),
                angle_deg=float(c.get_rotation_degrees() or 0.0) % 360.0, fields=fields)
            footprints.append(fp)
            by_index[i] = fp

        custom_regions = set()
        pads: List[Pad] = []
        for k, ap in enumerate(doc.pads):
            fp = by_index.get(ap.component_index) if ap.component_index is not None else None
            pad = self._pad(k, ap, fp, custom_regions)
            if pad is None:
                continue
            pads.append(pad)
            if fp is not None:
                fp.pad_ids.append(pad.id)
        self.custom_regions = custom_regions
        footprints = [f for f in footprints if f.reference or f.pad_ids]
        return footprints, pads

    def _pad_layers(self, ap) -> List[int]:
        """The signal layers (legacy) the pad has copper on: its own layer, or every
        signal layer of the stack for a multi-layer pad, less its removed lands."""
        if ap.layer == MULTI_LAYER:
            layers = [l for l in self.stack.order if not is_plane(l)]
        elif ap.layer in self.copper and not is_plane(ap.layer):
            layers = [ap.layer]
        else:
            return []
        if ap.layer == MULTI_LAYER and len(layers) > 2:
            from altium_monkey import PcbLayer
            kept = []
            for l in layers:
                try:
                    removed = l not in (layers[0], layers[-1]) and ap.is_copper_land_removed(
                        PcbLayer(l))
                except Exception:  # noqa: BLE001 - a pad with no removed-land map
                    removed = False
                if not removed:
                    kept.append(l)
            layers = kept
        return layers

    def _pad_size(self, ap, layer: int) -> Tuple[int, float, float, float]:
        """(shape, width, height, corner radius) of the pad on legacy ``layer``, in mm."""
        from altium_monkey import PcbLayer
        mode = int(ap.pad_mode or 0)
        if mode == 0 or layer == TOP:
            shape, w, h = ap.top_shape, ap.top_width, ap.top_height
        elif layer == BOTTOM:
            shape, w, h = ap.bot_shape, ap.bot_width, ap.bot_height
        elif mode == 2 and len(ap.inner_size_x or []) >= layer - 1:
            i = layer - 2
            shape = ap.inner_shape[i] if i < len(ap.inner_shape or []) else ap.mid_shape
            w, h = ap.inner_size_x[i], ap.inner_size_y[i]
        else:
            shape, w, h = ap.mid_shape, ap.mid_width, ap.mid_height
        try:
            corner = float(ap.corner_radius_mils_on_layer(PcbLayer(layer)) or 0) * MM_PER_MIL
        except Exception:  # noqa: BLE001
            corner = 0.0
        # A rounded rectangle is stored as a round pad with an alternate shape and a
        # corner radius; the radius says which it is.
        if corner > 0:
            shape = ROUNDED_RECTANGLE
        return int(shape or 0), _mm(w), _mm(h), corner

    def _pad(self, k: int, ap, fp: Optional[Footprint], custom_regions: set) -> Optional[Pad]:
        from shapely import affinity
        x, y = _mm(ap.x), _mm(ap.y)
        rot = float(ap.rotation or 0.0)
        shapes: Dict[int, List[Poly]] = {}
        custom = getattr(ap, "custom_shape", None)
        custom_layers = dict(getattr(custom, "layer_shapes", None) or {}) if custom else {}
        for layer in self._pad_layers(ap):
            g = None
            cs = custom_layers.get(layer)
            region = getattr(cs, "shape_region", None) if cs is not None else None
            if region is not None:
                custom_regions.add(id(region))
                g = region_geom(region)
            if g is None:
                shape, w, h, corner = self._pad_size(ap, layer)
                g = pad_shape(shape, w, h, corner)
                if g is not None:
                    g = affinity.translate(affinity.rotate(g, rot, origin=(0, 0)), x, y)
            if g is not None and not g.is_empty:
                polys = shapely_to_polys(self.frame.geom(g))
                if polys:
                    shapes[self.stack.ids[layer]] = polys
        hole = _mm(ap.hole_size)
        drill = (round(hole, NM), round(hole, NM))
        if hole > 0 and int(ap.hole_shape or 0) == HOLE_SLOT and _mm(ap.slot_size) > hole:
            slot = round(_mm(ap.slot_size), NM)
            # The slot lies along the pad's x unless turned a quarter turn in the pad.
            turned = abs(((float(ap.slot_rotation or 0.0) % 180.0) - 90.0)) < 45.0
            drill = (drill[0], slot) if turned else (slot, drill[1])
        if hole > 0:
            ptype = "pth" if (ap.is_plated and shapes) else "npth"
        else:
            ptype = "smd"
        if not shapes and hole <= 0:
            return None                  # a pad on a non-copper layer only (paste, mask)
        return Pad(id=f"pad{k}", net=self.net(ap.net_index),
                   footprint=fp.reference if fp is not None else "",
                   number=str(ap.designator or ""), position=self.frame.units(ap.x, ap.y),
                   pad_type=ptype, drill_mm=drill, shapes=shapes, angle_deg=rot % 360.0)

    # ----------------------------------------------------------------- vias
    def _vias(self) -> List[Via]:
        st = self.stack
        signal = [l for l in st.order if not is_plane(l)]
        outer = {st.ids[st.order[0]], st.ids[st.order[-1]]}
        all_ids = [st.ids[l] for l in st.order]
        out = []
        for k, v in enumerate(self.doc.vias):
            a, b = int(v.layer_start or TOP), int(v.layer_end or BOTTOM)
            if a in st.order and b in st.order:
                i, j = sorted((st.order.index(a), st.order.index(b)))
                span_legacy = st.order[i:j + 1]
            else:
                span_legacy = list(st.order)
            span = [st.ids[l] for l in span_legacy]
            if len(span) < 2:
                continue
            diam = _mm(v.diameter)
            by_layer = list(v.diameter_by_layer or [])
            removed = list(v.is_pad_removed or [])
            pad_mm: Dict[int, float] = {}
            for l in span_legacy:
                if is_plane(l):
                    continue                 # the plane is the via's copper there
                d = _mm(by_layer[l - 1]) if l - 1 < len(by_layer) and by_layer[l - 1] else diam
                inner = l in signal[1:-1] and l not in (span_legacy[0], span_legacy[-1])
                if inner and l - 1 < len(removed) and removed[l - 1]:
                    continue
                pad_mm[st.ids[l]] = round(d, NM)
            if span == all_ids:
                vtype = "through"
            elif span[0] in outer or span[-1] in outer:
                vtype = "blind"
            else:
                vtype = "buried"
            at = self.frame.units(v.x, v.y)
            out.append(Via(id=f"via{k}", net=self.net(v.net_index), position=at,
                           drill_mm=round(_mm(v.hole_size), NM),
                           diameter_mm=round(max(pad_mm.values(), default=diam), NM),
                           layers=span, via_type=vtype, pad_mm=pad_mm))
        return out

    # ----------------------------------------------------------------- tracks
    def _tracks(self) -> Tuple[List[Track], Dict[int, list]]:
        """The signal layers' tracks and arcs, and the plane layers' split lines (file
        frame, shapely) by layer."""
        st = self.stack
        tracks: List[Track] = []
        splits: Dict[int, list] = defaultdict(list)
        for t in self.doc.tracks:
            l = int(t.layer)
            if l not in self.copper or getattr(t, "is_keepout", False):
                continue
            a, b = (_mm(t.start_x), _mm(t.start_y)), (_mm(t.end_x), _mm(t.end_y))
            w = _mm(t.width)
            if is_plane(l):
                splits[l].append(stroke([a, b], w))
                continue
            if w <= 0:
                continue
            tracks.append(Track(net=self.net(t.net_index), layer=st.ids[l], width_mm=round(w, NM),
                                start=self.frame.pt(*a), end=self.frame.pt(*b)))
        for t in self.doc.arcs:
            l = int(t.layer)
            if l not in self.copper or getattr(t, "is_keepout", False):
                continue
            cx, cy, r, w = _mm(t.center_x), _mm(t.center_y), _mm(t.radius), _mm(t.width)
            a0, a1 = float(t.start_angle), float(t.end_angle)
            if is_plane(l):
                splits[l].append(stroke(arc_points(cx, cy, r, a0, a1), w))
                continue
            if w <= 0 or r <= 0:
                continue
            sweep = (a1 - a0) % 360.0 or 360.0
            # A full circle is two half circles: an arc track needs distinct ends.
            pieces = [(a0, a0 + 180.0), (a0 + 180.0, a0 + 360.0)] if sweep > 359.999 \
                else [(a0, a0 + sweep)]
            for s, e in pieces:
                at = [self.frame.pt(cx + r * math.cos(math.radians(a)),
                                    cy + r * math.sin(math.radians(a))) for a in (s, (s + e) / 2, e)]
                tracks.append(Track(net=self.net(t.net_index), layer=st.ids[l],
                                    width_mm=round(w, NM), start=at[0], end=at[2], mid=at[1]))
        return tracks, splits

    # ----------------------------------------------------------------- areas
    def _add_area(self, key: str, net: str, name: str, layer: int, g) -> None:
        if g is None or g.is_empty:
            return
        entry = self.areas.setdefault(key, (net, name, defaultdict(list)))
        entry[2][self.stack.ids[layer]].append(g)

    def _fills(self) -> None:
        from shapely import affinity
        from shapely.geometry import box
        for f in self.doc.fills:
            l = int(f.layer)
            if l not in self.copper or is_plane(l) or getattr(f, "is_keepout", False):
                continue
            x1, y1, x2, y2 = _mm(f.pos1_x), _mm(f.pos1_y), _mm(f.pos2_x), _mm(f.pos2_y)
            g = box(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            if f.rotation:
                g = affinity.rotate(g, float(f.rotation), origin=((x1 + x2) / 2, (y1 + y2) / 2))
            net = self.net(f.net_index)
            self._add_area(f"fill:{net}", net, "", l, g)

    def _regions(self) -> None:
        polygons = list(self.doc.polygons)
        regions = list(self.doc.shapebased_regions) or list(self.doc.regions)
        for r in regions:
            l = int(r.layer)
            if (l not in self.copper or is_plane(l) or r.is_keepout
                    or getattr(r, "is_board_cutout", False)
                    or int(getattr(r, "kind", REGION_COPPER)) != REGION_COPPER
                    or id(r) in self.custom_regions):
                continue
            g = region_geom(r)
            pi = r.polygon_index
            if pi is not None and pi != NO_INDEX and 0 <= int(pi) < len(polygons):
                poly = polygons[int(pi)]
                net = self.net(poly.net if isinstance(poly.net, int) else
                               (self.net_names.index(poly.net) if poly.net in self.net_names
                                else None))
                self._add_area(f"polygon:{int(pi)}", net, str(poly.name or ""), l, g)
            else:
                net = self.net(r.net_index)
                self._add_area(f"region:{net}", net, "", l, g)

    def _zones(self) -> List[Zone]:
        import shapely
        zones = []
        for key, (net, name, by_layer) in self.areas.items():
            filled = {}
            for lid, gs in by_layer.items():
                polys = shapely_to_polys(self.frame.geom(shapely.union_all(gs)))
                if polys:
                    filled[lid] = polys
            if filled:
                zones.append(Zone(id=key, net=net, name=name, priority=0, filled=filled))
        return zones

    # ----------------------------------------------------------------- outline
    def _outline(self):
        """The board's shape in the file's frame (shapely), less its cutouts, or None."""
        import shapely
        from shapely.geometry import Polygon
        ol = getattr(self.doc.board, "outline", None)
        verts = list(getattr(ol, "vertices", None) or [])
        ring = vertex_ring(
            (v.x_mils * MM_PER_MIL, v.y_mils * MM_PER_MIL, bool(v.is_arc),
             v.center_x_mils * MM_PER_MIL, v.center_y_mils * MM_PER_MIL,
             v.radius_mils * MM_PER_MIL, float(v.start_angle_deg or 0.0),
             float(v.end_angle_deg or 0.0)) for v in verts)
        if len(ring) < 3:
            self.progress.warn("The board has no outline; the 3D view shows no board body")
            return None
        g = Polygon(ring)
        if not g.is_valid:
            g = shapely.make_valid(g)
        cutouts = [region_geom(r) for r in (self.doc.shapebased_regions or [])
                   if getattr(r, "is_board_cutout", False)
                   or int(getattr(r, "kind", 0)) == REGION_BOARD_CUTOUT]
        cutouts = [c for c in cutouts if c is not None and not c.is_empty]
        if cutouts:
            g = g.difference(shapely.union_all(cutouts))
            self.progress.info(f"{len(cutouts)} board cutouts")
        return g

    # ----------------------------------------------------------------- planes
    def _planes(self, outline, pads: List[Pad], vias: List[Via], splits: Dict[int, list]):
        """Each internal plane's copper: the board less a pull-back from its edge, split
        into its areas by its split lines, each area on the net most of the holes in it
        are on (the plane's own net when it is not split), less a clearance about every
        hole of another net. Thermal reliefs are taken as solid connections."""
        import shapely
        from shapely.geometry import Point
        if outline is None:
            self.progress.warn("The planes cannot be made without a board outline")
            return
        plane_nets = dict(getattr(self.doc.board, "plane_net_names_by_index", None) or {})
        # Every hole as (x, y in the file's frame, radius, net, KiPI-SI layers it reaches).
        # Pads and vias are named after their record ("pad12", "via7").
        holes = []
        for pad in pads:
            ap = self.doc.pads[int(pad.id[3:])]
            if _mm(ap.hole_size) <= 0:
                continue
            clear = _mm(getattr(ap, "cache_power_plane_clearance", 0)) or 0.254
            holes.append((_mm(ap.x), _mm(ap.y), _mm(ap.hole_size) / 2 + clear, pad.net, None))
        for v in vias:
            av = self.doc.vias[int(v.id[3:])]
            clear = _mm(getattr(av, "power_plane_clearance", 0)) or 0.254
            holes.append((_mm(av.x), _mm(av.y), v.drill_mm / 2 + clear, v.net, set(v.layers)))
        body = outline.buffer(-PLANE_PULLBACK_MM, quad_segs=QUAD_SEGS)
        split_any = False
        for l in self.stack.order:
            if not is_plane(l):
                continue
            lid = self.stack.ids[l]
            own = plane_nets.get(l - PLANE_1 + 1, "")
            here = [h for h in holes if h[4] is None or lid in h[4]]
            lines = [g for g in splits.get(l, []) if g is not None]
            area = body.difference(shapely.union_all(lines)) if lines else body
            split_any = split_any or bool(lines)
            for island in getattr(area, "geoms", [area]):
                if island.is_empty or island.geom_type != "Polygon":
                    continue
                inside = [h[3] for h in here if h[3] and island.contains(Point(h[0], h[1]))]
                net = own
                if lines or not own:
                    common = Counter(inside).most_common(1)
                    net = own if own and own in inside else (common[0][0] if common else own)
                if not net:
                    continue
                clear = [Point(h[0], h[1]).buffer(h[2], quad_segs=QUAD_SEGS)
                         for h in here if h[3] != net]
                g = island.difference(shapely.union_all(clear)) if clear else island
                self._add_area(f"plane:{l}:{net}", net, f"Plane {l - PLANE_1 + 1}", l, g)
        self.assumed.append(
            "Planes: each internal plane is the board less a 20 mil pull-back from its edge "
            "and a clearance about the holes of other nets; holes on its net connect solidly "
            "(no thermal reliefs)"
            + ("; a split plane's areas take the net most of their holes are on" if split_any
               else ""))

    # ----------------------------------------------------------------- the rest
    def _silkscreen(self) -> Dict[str, List[Poly]]:
        """The overlays' tracks, arcs, fills and regions. Text is not read."""
        from shapely.geometry import box
        sides = {TOP_OVERLAY: "top", BOTTOM_OVERLAY: "bottom"}
        parts: Dict[str, list] = {"top": [], "bottom": []}
        for t in self.doc.tracks:
            side = sides.get(int(t.layer))
            if side:
                parts[side].append(stroke([(_mm(t.start_x), _mm(t.start_y)),
                                           (_mm(t.end_x), _mm(t.end_y))], _mm(t.width)))
        for a in self.doc.arcs:
            side = sides.get(int(a.layer))
            if side:
                parts[side].append(stroke(arc_points(_mm(a.center_x), _mm(a.center_y),
                                                     _mm(a.radius), float(a.start_angle),
                                                     float(a.end_angle)), _mm(a.width)))
        for f in self.doc.fills:
            side = sides.get(int(f.layer))
            if side:
                x1, y1, x2, y2 = _mm(f.pos1_x), _mm(f.pos1_y), _mm(f.pos2_x), _mm(f.pos2_y)
                parts[side].append(box(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
        for r in self.doc.shapebased_regions:
            side = sides.get(int(r.layer))
            if side:
                parts[side].append(region_geom(r))
        parts = {s: [self.frame.geom(g) for g in gs if g is not None and not g.is_empty]
                 for s, gs in parts.items()}
        return silk.merge(parts)

    def _net_classes(self) -> Dict[str, str]:
        """Each net's class: the first net class (not Altium's own "All Nets") it is in."""
        out: Dict[str, str] = {}
        for c in getattr(self.doc, "net_classes", None) or []:
            kind = getattr(c, "kind", 0)
            if int(getattr(kind, "value", kind) or 0) != 0:
                continue
            name = (c.name or "").strip()
            if not name or re.match(r"all\b", name, re.IGNORECASE):
                continue
            for member in c.members or []:
                out.setdefault(str(member), name)
        return out
