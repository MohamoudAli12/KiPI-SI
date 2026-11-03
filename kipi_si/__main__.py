"""Command-line entry point.

    python -m kipi_si                      # standalone: open board files from the window
    python -m kipi_si board.kipi_si.json.gz   # standalone, opening this board file
    python -m kipi_si --dump out.json.gz   # extract from the running KiCad and save, no GUI

Started from a terminal, KiPI-SI runs standalone and needs no KiCad. To run the plugin
workflow from a terminal instead (connect to the running KiCad PCB editor), set
``KIPI_SI_HOST=plugin``; ``--snapshot`` then opens a saved snapshot beside it.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="kipi_si", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board", nargs="?", help="board file to open")
    ap.add_argument("--snapshot", help="open a saved board snapshot (same as BOARD)")
    ap.add_argument("--dump", metavar="PATH", help="extract from KiCad, save snapshot, exit")
    ap.add_argument("--refill", action="store_true", help="refill zones before extracting")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args(argv)
    path = args.board or args.snapshot
    missing = missing_packages()
    if missing:
        print(f"This Python ({sys.executable}) does not have KiPI-SI's packages "
              f"({', '.join(missing)} are missing).\n\nStart KiPI-SI with kipi_si_launcher.py "
              "instead: it installs them into an environment of its own the first time.\n"
              f"    python \"{Path(__file__).resolve().parents[1] / 'kipi_si_launcher.py'}\"",
              file=sys.stderr)
        return 2

    from kipi_si.gui.app import setup_logging
    setup_logging(logging.DEBUG if args.debug else logging.INFO)

    if args.dump:
        from kipi_si.sources.kicad_ipc.extract import connect, extract_board
        from kipi_si.core.model.snapshot_io import save
        from kipi_si.core.progress import ProgressReporter
        prog = ProgressReporter()
        kicad, board = connect(progress=prog)
        snap = extract_board(board, refill_zones=args.refill, progress=prog)
        snap.kicad_version = str(kicad.get_version())
        save(snap, args.dump)
        print(f"Saved {args.dump}")
        return 0

    from kipi_si.host import Host, detect, set_current
    host = detect()
    set_current(host)
    source = None
    if host is Host.STANDALONE and path:
        source = _open(path)
        if source is None:
            return 2

    from kipi_si.gui import single_instance
    instance = single_instance.claim()
    if instance is None:
        print("KiPI-SI is already running", file=sys.stderr)
        return 0
    try:
        if host is Host.STANDALONE:
            from kipi_si.gui.app import run
            from kipi_si.sources.kicad_ipc.source import KiCadPartModels
            return run(source=source, tool=KiCadPartModels(), instance=instance)
        if path:
            from kipi_si.gui.app import run
            from kipi_si.core.model.snapshot_io import load
            from kipi_si.sources.kicad_ipc.source import InstalledKiCad, KiCadLiveSource
            # Load from KiCad still works: it connects on first use.
            source = KiCadLiveSource()
            return run(source=source, tool=InstalledKiCad(source),
                       snapshot=load(path), instance=instance)
        return _run_live(instance)
    finally:
        instance.release()


# The modules of requirements-standalone.txt, by the name they are imported under.
_MODULES = ("qtpy", "PySide6", "pyvista", "pyvistaqt", "numpy", "shapely", "scipy",
            "triangle", "pyamg", "plotly", "matplotlib", "yaml")


def missing_packages():
    """KiPI-SI's packages this Python cannot import, without importing any of them."""
    import importlib.util
    return [m for m in _MODULES if importlib.util.find_spec(m) is None]


def _open(path):
    """The source for the board file ``path``, or None (said on stderr) if KiPI-SI cannot
    read it."""
    from kipi_si.sources import registry
    if not Path(path).exists():
        print(f"No such file: {path}", file=sys.stderr)
        return None
    try:
        return registry.open_board(path)
    except ValueError as e:
        print(e, file=sys.stderr)
        return None


def _run_live(instance) -> int:
    from kipi_si.gui.app import run
    from kipi_si.sources.kicad_ipc.extract import ExtractionError, connect
    from kipi_si.sources.kicad_ipc.source import InstalledKiCad, KiCadLiveSource
    from kipi_si.core.progress import ProgressReporter
    try:
        kicad, board = connect(progress=ProgressReporter())
    except ExtractionError as e:
        print(e, file=sys.stderr)
        return 1
    source = KiCadLiveSource(kicad, board)
    return run(source=source, tool=InstalledKiCad(source), instance=instance)


if __name__ == "__main__":
    # Windows, started windowed (the launcher): on to KiPI-SI.exe, so Task Manager shows KiPI-SI
    # rather than Python (#124).
    from kipi_si.launcher.named_exe import relaunch
    code = relaunch(["-m", "kipi_si", *sys.argv[1:]])
    sys.exit(main() if code is None else code)
