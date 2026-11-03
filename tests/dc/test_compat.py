"""Results files saved by earlier KiPI-SI versions, before the modules moved into
kipi_si.core and kipi_si.dc, and results of electro-thermal solves."""
import gzip
import pickle
import re

import pytest

from kipi_si import compat
from kipi_si.core.results_io import LegacyResults
from kipi_si.dc.pi.report import load_results, save_results
from kipi_si.dc.thermal.cosim import solve_electrothermal
from kipi_si.dc.thermal.model import ThermalSettings
from kipi_si.dc.viz.results import build_result_scene
from tree_boards import board, setup


@pytest.mark.parametrize("old, new", [
    (("kipi_si.pi.tree", "TreeResult"), ("kipi_si.dc.pi.tree", "TreeResult")),
    (("kipi_si.solver.post", "ViaResult"), ("kipi_si.dc.solver.post", "ViaResult")),
    (("kipi_si.solver.direct", "DirectFactor"), ("kipi_si.core.solver.direct", "DirectFactor")),
    (("kipi_si.solver.fem", "_Factor"), ("kipi_si.core.solver.spd", "SpdSolver")),
    (("kipi_si.viz.results", "ResultScene"), ("kipi_si.dc.viz.results", "ResultScene")),
    (("kipi_si.viz.meshes", "NetScene"), ("kipi_si.core.viz.meshes", "NetScene")),
    (("kipi_si.mesh.mesher", "NetMesh"), ("kipi_si.core.mesh.mesher", "NetMesh")),
    (("kipi_si.model.board", "Pad"), ("kipi_si.core.model.board", "Pad")),
    (("kipi_si.thermal.cosim", "ThermalResult"), ("kipi_si.dc.thermal.cosim", "ThermalResult")),
    (("kipi_si.core.kicad_io.snapshot", "load"), ("kipi_si.core.model.snapshot_io", "load")),
    (("kipi_si.kicad_io.snapshot", "load"), ("kipi_si.core.model.snapshot_io", "load")),
    (("kipi_si.dc.pi.tree", "TreeResult"), ("kipi_si.dc.pi.tree", "TreeResult")),
    (("numpy", "ndarray"), ("numpy", "ndarray")),
])
def test_moved_modules(old, new):
    assert compat.moved(*old) == new


def _solved():
    snap = board()
    s = setup("ldo", iq=0.01, ground=True)
    s.thermal = ThermalSettings(enabled=True, iterations=2)
    tree = solve_electrothermal(snap, s, s.thermal)
    temp = tree.thermal.sampler()
    scenes = {n: build_result_scene(snap, g.result, temperature=temp)
              for n, g in tree.groups.items()}
    return snap, s, tree, scenes


@pytest.fixture(scope="module")
def solved():
    return _solved()


def test_electrothermal_results_save_and_load(solved, tmp_path):
    snap, s, tree, scenes = solved
    back = load_results(save_results(tmp_path / "r.kipi_si-results", tree, snap, s))
    assert back["tree"].thermal.t_max == pytest.approx(tree.thermal.t_max)
    assert [l.drop for l in back["tree"].loads] == [l.drop for l in tree.loads]
    # The live temperature field is not saved; its effect on resistivity is.
    r = back["tree"].groups[tree.loads[0].group].result.solution
    assert r.problem.temperature is None and r.tri_rho_factor is not None


class _OldPaths(pickle._Pickler):
    """Names classes by where 0.6 kept them: kipi_si.core.x and kipi_si.dc.x were kipi_si.x."""

    def save_global(self, obj, name=None):
        name = name or getattr(obj, "__qualname__", None) or obj.__name__
        module = pickle.whichmodule(obj, name)
        if not module.startswith("kipi_si."):
            return super().save_global(obj, name)
        self.save(re.sub(r"^kipi_si\.(?:core|dc)\.", "kipi_si.", module))
        self.save(name)
        self.write(pickle.STACK_GLOBAL)
        self.memoize(obj)


def test_results_saved_with_the_old_module_paths_still_load(solved, tmp_path):
    snap, s, tree, scenes = solved
    payload = {"format": 1, "saved": "2026-01-01 00:00:00",
               "board": snap.board_name, "tree": tree, "scenes": scenes, "setup": s}
    path = tmp_path / "old.kipi_si-results"
    with gzip.open(path, "wb") as fh:
        _OldPaths(fh, protocol=4).dump(payload)
    with gzip.open(path, "rb") as fh:
        old = fh.read()
    assert b"kipi_si.pi.results" in old and b"kipi_si.dc." not in old and b"kipi_si.core." not in old
    with pytest.raises(ModuleNotFoundError):
        pickle.loads(old)
    with pytest.raises(LegacyResults):
        load_results(path)                      # pickles open only when asked for (#99)
    back = load_results(path, legacy=True)
    assert back["legacy"]
    assert type(back["tree"]).__module__ == "kipi_si.dc.pi.results"
    assert [l.drop for l in back["tree"].loads] == [l.drop for l in tree.loads]
    name = next(iter(scenes))
    assert type(back["scenes"][name]).__module__ == "kipi_si.dc.viz.results"


def test_results_file_names_say_whether_thermal_was_solved(solved):
    from kipi_si.dc.pi.report import results_suffix
    from kipi_si.dc.pi.tree import solve_tree
    snap, s, tree, _ = solved
    assert results_suffix(tree) == ".kipi_si-dc-thermal-results"
    assert results_suffix(solve_tree(snap, setup("ldo"))) == ".kipi_si-dc-results"
