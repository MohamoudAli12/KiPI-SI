"""Parts' 3D models from the STEP files embedded in an Altium board.

Each part's 3D bodies name an embedded model and say where it goes: turned about the
model's own X, Y and Z axes (in that order), lifted by ``dz``, then turned about the board's
Z by the body's 2D rotation and moved to its 2D position. A part on the bottom is turned over
about the board's X axis (y and z reversed) and hangs under the board; checked against the
pads of the asymmetric bottom parts (LEDs, a switch, a connector) of the Pi.MX8 boards.

The STEP files are turned into triangles by ``wn-geometer`` (which altium-monkey brings),
each model once however many parts use it. Its glTF keeps the STEP's frame (Z up), in
metres. Meshes come out in the 3D view's frame (see
:func:`kipi_si.sources.kicad_ipc.models3d.to_mesh`): mm, board y up, z = 0 at the bottom of a
board ``board_mm`` thick.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np

from kipi_si.core.progress import NULL, ProgressReporter
from kipi_si.sources.base import ModelProvider

MM_PER_UNIT = 0.0254 / 10000.0
#: Bigger models are not drawn: they would slow the view more than they show.
MAX_TRIANGLES = 400_000


def _rot(axis: str, deg: float) -> np.ndarray:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def body_transform(rotx: float, roty: float, rotz: float, dz_mm: float, rot2d: float,
                   x_mm: float, y_mm: float, bottom: bool):
    """(3x3 matrix, offset): a model point p (mm) on the board at ``M @ p + offset``, in
    the file's frame (y up, z = 0 on the side the part is on, up away from the board)."""
    m = _rot("z", rotz) @ _rot("y", roty) @ _rot("x", rotx)
    lift = np.array([0.0, 0.0, dz_mm])
    flip = np.diag([1.0, -1.0, -1.0]) if bottom else np.eye(3)
    place = _rot("z", rot2d)
    total = place @ flip @ m
    offset = place @ flip @ lift + np.array([x_mm, y_mm, 0.0])
    return total, offset


class EmbeddedModels(ModelProvider):
    """The models embedded in the ``.PcbDoc`` at ``path``, for a board ``board_mm`` thick."""
    label = "the models embedded in the Altium board"

    def __init__(self, path, board_mm: float):
        self.path = Path(path)
        self.board_mm = float(board_mm)
        self._meshes: Dict[str, Optional[tuple]] = {}   # model id -> (points mm, tris, rgb)

    def load(self, refs: Iterable[str],
             progress: ProgressReporter = NULL) -> Dict[str, Optional[object]]:
        from kipi_si.sources.altium.reader import open_doc
        refs = sorted(set(refs))
        result: Dict[str, Optional[object]] = {r: None for r in refs}
        doc = open_doc(self.path)
        ox = float(doc.board.origin_x or 0) * 0.0254
        oy = float(doc.board.origin_y or 0) * 0.0254
        index = {(c.designator or "").strip(): i for i, c in enumerate(doc.components)}
        sides = {i: str(c.layer).upper() == "BOTTOM" for i, c in enumerate(doc.components)}
        model_index = {m.id: k for k, m in enumerate(doc.models)}
        bodies: Dict[int, list] = {}
        for b in doc.component_bodies:
            if b.component_index is not None and b.model_id:
                bodies.setdefault(int(b.component_index), []).append(b)
        for ref in refs:
            progress.check_cancel()
            ci = index.get(ref)
            if ci is None:
                continue
            pieces = []
            for b in bodies.get(ci, []):
                mesh = self._model(doc, model_index.get(b.model_id), progress)
                if mesh is None:
                    continue
                pts, tris, rgb = mesh
                bottom = sides[ci]
                m, off = body_transform(
                    float(b.model_3d_rotx or 0), float(b.model_3d_roty or 0),
                    float(b.model_3d_rotz or 0), float(b.model_3d_dz or 0) * MM_PER_UNIT,
                    float(b.model_2d_rotation or 0), float(b.model_2d_x or 0) * MM_PER_UNIT,
                    float(b.model_2d_y or 0) * MM_PER_UNIT, bottom)
                placed = pts @ m.T + off
                placed[:, 0] -= ox
                placed[:, 1] -= oy
                if not bottom:
                    placed[:, 2] += self.board_mm
                pieces.append((placed, tris, rgb))
            if pieces:
                result[ref] = _to_mesh(pieces)
        n = sum(v is not None for v in result.values())
        if refs and n < len(refs):
            progress.info(f"3D models: {len(refs) - n} part(s) have no model embedded in "
                          f"{self.path.name}")
        return result

    def _model(self, doc, k: Optional[int], progress: ProgressReporter):
        """Model ``k`` (an index into the board's models) as triangles in mm, or None."""
        if k is None:
            return None
        key = doc.models[k].id
        if key in self._meshes:
            return self._meshes[key]
        mesh = None
        name = doc.models[k].name or key
        try:
            data = doc.get_embedded_model_payload(k)
            if data:
                import geometer
                from kipi_si.core.viz.glb import read_glb
                parts = read_glb(geometer.step_to_glb(bytes(data))).values()
                pts, tris, rgb, base = [], [], [], 0
                for p in parts:
                    pts.append(np.asarray(p.points, float) * 1000.0)
                    tris.append(np.asarray(p.tris) + base)
                    rgb.append(np.asarray(p.rgb))
                    base += len(p.points)
                if pts and sum(len(t) for t in tris) <= MAX_TRIANGLES:
                    mesh = (np.vstack(pts), np.vstack(tris), np.vstack(rgb))
                elif pts:
                    progress.info(f"3D model {name} is too detailed to show")
        except Exception as e:  # noqa: BLE001 - a model is a nicety; never fail on one
            progress.info(f"3D model {name} could not be read: {e}")
        self._meshes[key] = mesh
        return mesh


def _to_mesh(pieces: List[tuple]):
    from kipi_si.core.viz.polydata import set_cell_array, triangles
    pts, tris, rgb, base = [], [], [], 0
    for p, t, c in pieces:
        pts.append(p)
        tris.append(t + base)
        rgb.append(c)
        base += len(p)
    mesh = triangles(np.vstack(pts), np.vstack(tris))
    set_cell_array(mesh, "rgb", np.vstack(rgb).astype(np.uint8))
    return mesh
