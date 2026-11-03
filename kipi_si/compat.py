"""Reading files written by earlier KiPI-SI versions.

Results files before 0.8.0 are pickles, which name the module of every object they hold
(0.8.0 writes JSON and arrays instead, see :mod:`kipi_si.core.results_io`). KiPI-SI 0.7.0
moved its modules into ``kipi_si.core`` (shared) and ``kipi_si.dc`` (DC analysis), and 0.8.0
moved the parts of ``kipi_si.core.kicad_io`` that are not KiCad-specific into the rest of
``kipi_si.core`` and the KiCad reader itself to ``kipi_si.sources.kicad_ipc``; the table below
maps the old module paths to the new ones so results saved before still open.
"""

from __future__ import annotations

import pickle
from typing import Tuple

# Old module path (or prefix) -> new one, most specific first.
_MOVED_MODULES = (
    ("kipi_si.core.kicad_io.snapshot", "kipi_si.core.model.snapshot_io"),
    ("kipi_si.kicad_io.snapshot", "kipi_si.core.model.snapshot_io"),
    ("kipi_si.core.kicad_io", "kipi_si.sources.kicad_ipc"),
    ("kipi_si.solver.direct", "kipi_si.core.solver.direct"),
    ("kipi_si.viz.results", "kipi_si.dc.viz.results"),
    ("kipi_si.viz", "kipi_si.core.viz"),
    ("kipi_si.gui.pi_panel", "kipi_si.dc.gui.pi_panel"),
    ("kipi_si.progress", "kipi_si.core.progress"),
    ("kipi_si.model", "kipi_si.core.model"),
    ("kipi_si.kicad_io", "kipi_si.sources.kicad_ipc"),
    ("kipi_si.geometry", "kipi_si.core.geometry"),
    ("kipi_si.mesh", "kipi_si.core.mesh"),
    ("kipi_si.solver", "kipi_si.dc.solver"),
    ("kipi_si.pi", "kipi_si.dc.pi"),
    ("kipi_si.thermal", "kipi_si.dc.thermal"),
    ("kipi_si.report", "kipi_si.dc.report"),
)
# Classes that moved to another module or were renamed: (old module, old name) -> new.
_MOVED_CLASSES = {
    ("kipi_si.solver.fem", "_Factor"): ("kipi_si.core.solver.spd", "SpdSolver"),
}


def moved(module: str, name: str) -> Tuple[str, str]:
    """Where ``module.name`` of an earlier KiPI-SI lives now (unchanged if it did not move)."""
    if (module, name) in _MOVED_CLASSES:
        return _MOVED_CLASSES[(module, name)]
    for old, new in _MOVED_MODULES:
        if module == old or module.startswith(old + "."):
            return new + module[len(old):], name
    return module, name


# What a results pickle may name besides KiPI-SI's own classes (#99): NumPy arrays, the
# pyvista/VTK meshes and k-d trees of the 3D views, and a few builtin containers.
_LEGACY_GLOBALS = {
    ("builtins", n) for n in ("set", "frozenset", "complex", "list", "dict", "tuple", "slice",
                              "range", "bytearray", "bytes", "int", "float", "str", "bool")
} | {
    ("collections", "defaultdict"), ("collections", "OrderedDict"),
    ("copyreg", "_reconstructor"), ("numpy", "dtype"), ("numpy", "ndarray"),
    ("vtkmodules.util.pickle_support", "unserialize_VTK_data_object"),
} | {
    (f"numpy.{core}.{m}", n) for core in ("core", "_core")
    for m, n in (("multiarray", "_reconstruct"), ("multiarray", "scalar"),
                 ("numeric", "_frombuffer"))
}
# Packages whose classes (not functions) a results pickle may name.
_LEGACY_PACKAGES = ("kipi_si.core.", "kipi_si.dc.", "kipi_si.ac.", "kipi_si.noise.", "kipi_si.si.",
                    "pyvista.",
                    "scipy.spatial.")
_PATHS = ("Path", "PosixPath", "WindowsPath", "PurePath", "PurePosixPath", "PureWindowsPath")


class Unpickler(pickle.Unpickler):
    """Reads the results pickles of KiPI-SI 0.7 and earlier: finds classes at their current
    module paths, and refuses anything a results file does not hold, such as functions that
    could run commands. Loading a pickle is still not safe, only less unsafe; KiPI-SI asks
    before it opens one."""

    def find_class(self, module, name):
        module, name = moved(module, name)
        # Python 3.13 and later pickle paths as pathlib._local.
        if module in ("pathlib", "pathlib._local") and name in _PATHS:
            from pathlib import Path        # a Windows path saved on Windows opens elsewhere
            return Path
        if (module, name) in _LEGACY_GLOBALS:
            return super().find_class(module, name)
        if module.startswith(_LEGACY_PACKAGES) and not name.startswith("_"):
            obj = super().find_class(module, name)
            if isinstance(obj, type):
                return obj
        raise pickle.UnpicklingError(f"Results file names {module}.{name}, which KiPI-SI "
                                     "results do not hold; it was not opened")
