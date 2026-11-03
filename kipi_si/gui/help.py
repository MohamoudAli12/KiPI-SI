"""The user guide: an HTML file that ships with the plugin, opened in the system browser."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from qtpy.QtWidgets import QMessageBox, QWidget

log = logging.getLogger("kipi_si")

_DOCS = Path(__file__).resolve().parents[2] / "docs"
# Shown when the local copy is missing (a partial install) or cannot be opened.
# GitHub Pages serves docs/ from main, so this is the rendered page, not its source.
ONLINE = "https://mohamoudali12.github.io/KiPI-SI/help.html"
# What PI analysis is and how KiPI-SI's solvers work (#92).
SOLVER_GUIDE_ONLINE = "https://mohamoudali12.github.io/KiPI-SI/solver-guide.html"


def help_path() -> Optional[Path]:
    """The user guide, which lives beside the package in the plugin folder."""
    p = _DOCS / "help.html"
    return p if p.is_file() else None


def solver_guide_url() -> str:
    """The Solver Guide: the copy installed with KiPI-SI, else the online one."""
    p = _DOCS / "solver-guide.html"
    if p.is_file():
        from qtpy.QtCore import QUrl
        return QUrl.fromLocalFile(str(p)).toString()
    return SOLVER_GUIDE_ONLINE


def open_help(parent: Optional[QWidget] = None) -> bool:
    """Open the user guide in the default browser. Falls back to Python's webbrowser
    module, then to telling the user where the file is. True if a browser was asked to
    open it."""
    path = help_path()
    if path is None:
        log.warning("User guide not found under %s", _DOCS)
        QMessageBox.information(parent, "KiPI-SI", f"The user guide is not installed with this "
                                                f"copy of KiPI-SI. It is online at:\n\n{ONLINE}")
        return False
    from kipi_si.gui.browser import open_in_browser
    if open_in_browser(path):
        return True
    QMessageBox.information(parent, "KiPI-SI", f"Could not open a web browser. The user guide "
                                            f"is at:\n\n{path}")
    return False
