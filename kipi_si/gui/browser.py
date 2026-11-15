"""Open a local file (an HTML report) or a URL (the user guide) in the default web browser."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from qtpy.QtCore import QUrl
from qtpy.QtGui import QDesktopServices

log = logging.getLogger(__name__)

# Set by or for KiPI-SI's own Python and Qt; a browser started from KiPI-SI must not inherit
# them.
_OWN_ENV = ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH", "VIRTUAL_ENV", "QT_API",
            "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH")


def _xdg_open(target) -> bool:
    """Linux: run ``xdg-open`` ourselves on a path or a URL. Qt hands the file to the
    desktop portal over D-Bus instead and reports success at once; where the portal runs
    without the display (a window manager started with startx, say) the browser then
    fails to start and nothing opens. ``xdg-open`` runs with KiPI-SI's own display. True
    if it started."""
    exe = shutil.which("xdg-open")
    if exe is None:
        return False
    env = {k: v for k, v in os.environ.items() if k not in _OWN_ENV}
    try:
        subprocess.Popen([exe, str(target)], env=env, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, close_fds=True)
    except OSError as e:
        log.warning("xdg-open could not start for %s: %s", target, e)
        return False
    return True


def _open(target, qurl: QUrl, uri: str) -> bool:
    if sys.platform.startswith("linux") and _xdg_open(target):
        return True
    if QDesktopServices.openUrl(qurl):
        return True
    try:
        import webbrowser
        if webbrowser.open(uri):
            return True
    except Exception as e:  # noqa: BLE001 - any browser failure is only logged
        log.warning("Could not open %s: %s", target, e)
    return False


def open_in_browser(path) -> bool:
    """Ask the desktop to open the file ``path``; fall back to Python's webbrowser module
    where Qt cannot (some Linux desktops without a handler). True if a browser was asked
    to open it."""
    path = Path(path).resolve()
    return _open(path, QUrl.fromLocalFile(str(path)), path.as_uri())


def open_url(url: str) -> bool:
    """Ask the desktop to open the web address ``url``, as :func:`open_in_browser` does a
    file. True if a browser was asked to open it."""
    return _open(url, QUrl(url), url)
