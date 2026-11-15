"""The user guide: the documentation site, opened in the system browser."""

from __future__ import annotations

import logging
from typing import Optional

from qtpy.QtWidgets import QMessageBox, QWidget

log = logging.getLogger("kipi_si")

# The Sphinx docs in docs/, published to GitHub Pages from main (.github/workflows/docs.yml).
ONLINE = "https://mohamoudali12.github.io/KiPI-SI/"
# What PI analysis is and how KiPI-SI's solvers work (#92): the site's Theory section.
SOLVER_GUIDE_ONLINE = ONLINE + "theory/index.html"


def solver_guide_url() -> str:
    """The Solver Guide, for the About box's link."""
    return SOLVER_GUIDE_ONLINE


def open_help(parent: Optional[QWidget] = None) -> bool:
    """Open the user guide in the default browser. Tells the user where it is if no
    browser opens. True if a browser was asked to open it."""
    from kipi_si.gui.browser import open_url
    if open_url(ONLINE):
        return True
    QMessageBox.information(parent, "KiPI-SI", f"Could not open a web browser. The user guide "
                                            f"is online at:\n\n{ONLINE}")
    return False
