"""Where the launcher keeps KiPI-SI's environment, and where KiPI-SI itself is.

The environment is per user, outside the KiPI-SI folder, so the folder can be read-only,
shared or replaced by a newer KiPI-SI without losing it:

* Windows: ``%LOCALAPPDATA%\\KiPI-SI``
* macOS: ``~/Library/Application Support/KiPI-SI``
* Linux: ``$XDG_DATA_HOME/kipi_si`` (``~/.local/share/kipi_si``)

``KIPI_SI_HOME`` puts it somewhere else.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Mapping, Optional

HOME_ENV = "KIPI_SI_HOME"

#: The KiPI-SI folder: the one holding the ``kipi_si`` package, ``requirements*.txt`` and docs.
KIPI_SI_ROOT = Path(__file__).resolve().parents[2]


def data_dir(environ: Optional[Mapping[str, str]] = None, platform: Optional[str] = None,
             home: Optional[Path] = None) -> Path:
    """The folder the launcher keeps everything in."""
    env = os.environ if environ is None else environ
    platform = platform or sys.platform
    home = home or Path.home()
    if env.get(HOME_ENV):
        return Path(env[HOME_ENV])
    if platform == "win32":
        base = env.get("LOCALAPPDATA")
        return Path(base) / "KiPI-SI" if base else home / "AppData" / "Local" / "KiPI-SI"
    if platform == "darwin":
        return home / "Library" / "Application Support" / "KiPI-SI"
    xdg = env.get("XDG_DATA_HOME")
    return (Path(xdg) if xdg else home / ".local" / "share") / "kipi_si"


def env_dir(data: Optional[Path] = None) -> Path:
    """KiPI-SI's virtual environment."""
    return (data or data_dir()) / "venv"


def env_python(env: Path, windowed: bool = False, platform: Optional[str] = None) -> Path:
    """The environment's Python; ``windowed`` is the one with no console (Windows)."""
    if (platform or sys.platform) == "win32":
        return env / "Scripts" / ("pythonw.exe" if windowed else "python.exe")
    return env / "bin" / "python"


def state_path(env: Path) -> Path:
    """What the launcher installed into ``env`` (see :mod:`kipi_si.launcher.state`)."""
    return env / "kipi_si-setup.json"


def log_dir(data: Optional[Path] = None) -> Path:
    return (data or data_dir()) / "logs"


def requirements_file(root: Path = KIPI_SI_ROOT) -> Path:
    """What KiPI-SI needs standalone (pyproject.toml's dependencies)."""
    return root / "requirements-standalone.txt"
