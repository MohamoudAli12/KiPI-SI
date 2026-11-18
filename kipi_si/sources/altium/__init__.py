"""Altium Designer boards (``.PcbDoc``, or the boards of a ``.PrjPcb``), read with the
optional `altium-monkey <https://pypi.org/project/altium-monkey/>`_ package."""

from __future__ import annotations

from kipi_si.sources.base import ReaderMissing

#: The package that reads Altium files, as pip names it, and what installs it with KiPI-SI.
PACKAGE = "altium-monkey"
EXTRA = "kipi_si[altium]"
#: The oldest Python it runs on.
MIN_PYTHON = (3, 12)


class AltiumUnavailable(ReaderMissing):
    """The optional reader is not installed (or cannot run on this Python)."""
    launcher_flag = "--add-altium"


def require():
    """Import the reader's package, or raise :class:`AltiumUnavailable` saying how to get
    it."""
    import sys
    if sys.version_info < MIN_PYTHON:
        raise AltiumUnavailable(
            "Altium boards are read with the altium-monkey package, which needs Python "
            f"{'.'.join(map(str, MIN_PYTHON))} or newer; KiPI-SI runs on Python "
            f"{sys.version_info.major}.{sys.version_info.minor}.")
    try:
        import altium_monkey  # noqa: F401
    except ImportError:
        raise AltiumUnavailable(
            "Altium boards need the optional altium-monkey package, which is not installed. "
            "Install it with the KiPI-SI launcher (kipi_si_launcher.py --add-altium), or "
            f"with: pip install {PACKAGE}") from None
    return altium_monkey


def available() -> bool:
    try:
        require()
        return True
    except AltiumUnavailable:
        return False
