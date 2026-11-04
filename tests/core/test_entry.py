"""The plugin entry point keeps other Pythons' folders off the path. KiCad starts a plugin
with its own PYTHONPATH (Arch: /usr/lib/python3.14/site-packages) whatever Python the plugin
runs on, and that Python's builds of PySide6 or numpy then shadow the venv's and fail."""

import os
import subprocess
import sys
from pathlib import Path

import kipi_si_entry as entry

ROOT = Path(__file__).resolve().parents[2]
OTHER = f"python{sys.version_info[0]}.{sys.version_info[1] + 1}"


def test_another_pythons_folders_are_foreign():
    assert entry.foreign_python_path("/usr/lib/python3.14/site-packages", (3, 13))
    assert entry.foreign_python_path("/usr/lib/python3.12/dist-packages", (3, 13))
    assert entry.foreign_python_path("/usr/lib/python3.14", (3, 13))
    assert entry.foreign_python_path("/usr/lib/python3.9/site-packages", (3, 13))


def test_this_pythons_and_other_folders_stay():
    venv = "/home/u/.cache/kicad/10.0/python-environments/x/lib/python3.13/site-packages"
    assert not entry.foreign_python_path(venv, (3, 13))
    assert not entry.foreign_python_path("/usr/lib/python3.13", (3, 13))
    assert not entry.foreign_python_path("/home/u/projects/KiPI", (3, 13))
    assert not entry.foreign_python_path("/home/u/python3.13.11-src/x", (3, 13))  # not X.Y
    assert not entry.foreign_python_path(r"C:\Program Files\KiCad\bin\Lib\site-packages",
                                         (3, 11))


def test_dropped_from_sys_path_and_pythonpath(monkeypatch):
    other = f"/usr/lib/{OTHER}/site-packages"
    monkeypatch.setattr(sys, "path", [other, *sys.path])
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join([other, "/keep/me"]))
    entry.drop_foreign_python_paths()
    assert other not in sys.path
    assert os.environ["PYTHONPATH"] == "/keep/me"
    monkeypatch.setenv("PYTHONPATH", other)
    entry.drop_foreign_python_paths()
    assert "PYTHONPATH" not in os.environ


def test_a_package_on_kicads_pythonpath_does_not_shadow_the_venvs(tmp_path):
    """As KiCad starts the plugin: another Python's site-packages first on PYTHONPATH, with
    a build of a package this Python also has (here yaml) that cannot load in this one."""
    site = tmp_path / "lib" / OTHER / "site-packages"
    (site / "yaml").mkdir(parents=True)
    (site / "yaml" / "__init__.py").write_text("raise ImportError('built for another Python')")
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import kipi_si_entry as e; "
            "e.drop_foreign_python_paths(); import yaml, os; "
            "print(yaml.__file__); print(os.environ.get('PYTHONPATH', ''))")
    env = dict(os.environ, PYTHONPATH=str(site))
    out = subprocess.run([sys.executable, "-c", code, str(ROOT)], env=env, cwd=tmp_path,
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    loaded, pythonpath = out.stdout.splitlines()
    assert OTHER not in loaded and pythonpath == ""
