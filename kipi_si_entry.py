"""KiCad IPC plugin action entry point (see plugin.json).

KiCad starts this in the plugin's own venv with KICAD_API_SOCKET / KICAD_API_TOKEN
set, so kipy connects to the instance that launched us.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_PYTHON_DIR = re.compile(r"python(\d+)\.(\d+)")


def foreign_python_path(path: str, version=sys.version_info) -> bool:
    """Whether ``path`` belongs to a Python other than this one (a ``pythonX.Y`` folder in it,
    such as /usr/lib/python3.14/site-packages).

    KiCad starts a plugin with its own PYTHONPATH, whatever interpreter the plugin is set to
    use. Arch's KiCad runs on the system Python 3.14 and so hands over
    /usr/lib/python3.14/site-packages; the plugin's venv runs on 3.13 (no 3.14 wheels for
    triangle), and the 3.14 builds there (PySide6, numpy) load ahead of the venv's and fail:
    "No module named 'shiboken6.Shiboken'", and the button does nothing. A sitecustomize.py
    put by hand into KiCad's venv once did this; KiCad rebuilds that venv, so it lives here.
    """
    for part in path.replace("\\", "/").lower().split("/"):
        m = _PYTHON_DIR.fullmatch(part)
        if m and (int(m[1]), int(m[2])) != tuple(version[:2]):
            return True
    return False


def drop_foreign_python_paths() -> None:
    """Take other Pythons' folders off sys.path, and out of PYTHONPATH for the processes
    KiPI-SI starts (pip for PARDISO, the help browser)."""
    sys.path[:] = [p for p in sys.path if not foreign_python_path(p)]
    if os.environ.get("PYTHONPATH"):
        kept = [p for p in os.environ["PYTHONPATH"].split(os.pathsep)
                if p and not foreign_python_path(p)]
        if kept:
            os.environ["PYTHONPATH"] = os.pathsep.join(kept)
        else:
            del os.environ["PYTHONPATH"]


def main() -> int:
    drop_foreign_python_paths()             # before anything imports Qt or numpy
    # Windows: on to KiPI-SI.exe, so Task Manager shows KiPI-SI rather than Python (#124).
    from kipi_si.launcher.named_exe import relaunch
    code = relaunch([os.path.abspath(__file__), *sys.argv[1:]])
    if code is not None:
        return code
    from kipi_si.gui import app as kipi_si_app
    from kipi_si.gui.app import run, setup_logging

    setup_logging(console=False)
    # KiCad captures plugin stdout/stderr through a pipe it does not always drain; a full
    # pipe blocks the writer forever. Send everything to this session's log folder.
    kipi_si_app.detach_std_streams()
    os.environ.setdefault("QT_API", "pyside6")
    from kipi_si.host import Host, set_current
    set_current(Host.PLUGIN)
    from kipi_si.gui import single_instance
    instance = single_instance.claim()
    if instance is None:        # another KiPI-SI is open; it was brought to the front
        return 0
    try:
        def connect_kicad():
            # Before anything loads MKL: finish a PARDISO removal asked for last time (#129).
            from kipi_si.gui import pardiso_setup
            pardiso_setup.startup()
            from kipi_si.core.progress import ProgressReporter
            from kipi_si.sources.kicad_ipc.extract import connect
            from kipi_si.sources.kicad_ipc.source import InstalledKiCad, KiCadLiveSource
            kicad, board = connect(progress=ProgressReporter())
            source = KiCadLiveSource(kicad, board)
            return source, InstalledKiCad(source)

        # The window first, so the click in KiCad is answered at once (#55); KiPI-SI connects
        # to KiCad once it is showing.
        return run(instance=instance, connect=connect_kicad)
    finally:
        instance.release()


if __name__ == "__main__":
    sys.exit(main())
