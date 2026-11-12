# Copyright (c) 2026 Tomachie LLC.
"""Line icons for the toolbar and buttons, drawn from small SVG paths in the window's text
colour, so they follow the dark or light theme (:func:`retint` is called on a switch).

Each icon is a 24 × 24 stroke drawing; :func:`attach` puts one on an action or button and
remembers it, so that a theme switch can draw it again in the new colour.
"""

from __future__ import annotations

import weakref
from typing import Dict

from qtpy.QtCore import QByteArray, QRectF, Qt
from qtpy.QtGui import QIcon, QPainter, QPalette, QPixmap
from qtpy.QtWidgets import QApplication

_PATHS: Dict[str, str] = {
    "open": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1'
            '-2-2z"/>',
    "reload": '<path d="M20 12a8 8 0 1 1-2.4-5.7"/><path d="M20 4v5h-5"/>',
    "save": '<path d="M5 3h11l5 5v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/>'
            '<path d="M7 3v5h8V3"/><path d="M7 21v-7h10v7"/>',
    "results": '<path d="M3 3v18h18"/><path d="M7 15l4-5 3 3 5-6"/>',
    "top": '<path d="M2 17l10 4 10-4-10-4z"/><path d="M12 2v8M9 7l3 3 3-3"/>',
    "bottom": '<path d="M2 7l10 4 10-4-10-4z"/><path d="M12 22v-8M9 17l3-3 3 3"/>',
    "iso": '<path d="M12 2l9 5v10l-9 5-9-5V7z"/><path d="M12 22V12M21 7l-9 5-9-5"/>',
    "camera": '<path d="M3 8a2 2 0 0 1 2-2h2l2-2h6l2 2h2a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2'
              ' 2 0 0 1-2-2z"/><circle cx="12" cy="13" r="3.5"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 12.5l9 5 9-5"/>'
              '<path d="M3 17l9 5 9-5"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.3a2.6 2.6 0 1 1 3.6 2.4c-.7.3-1.1'
            '.9-1.1 1.6v.7"/><path d="M12 17.2v.1"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><path d="M12 7.6v.1"/>',
    "moon": '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 '
           '17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "import": '<path d="M12 3v12M7 10l5 5 5-5"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 '
              '2-2v-2"/>',
    "wand": '<path d="M4 20L16 8"/><path d="M14 6l2-2 4 4-2 2z"/><path d="M6 3v3M4.5 4.5h3'
            'M19 14v3M17.5 15.5h3"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "copy": '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 '
            '2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
    "trash": '<path d="M4 7h16M10 11v6M14 11v6"/><path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 '
             '2-2l1-12M9 7V4h6v3"/>',
    "file": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>'
            '<path d="M14 3v5h5"/>',
}

_SIZE = 20                      # drawn at twice this for sharp edges on high-DPI screens
_attached: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def names():
    return sorted(_PATHS)


def icon(name: str, color=None) -> QIcon:
    """``name``'s icon, in ``color`` (default: the palette's text colour); a disabled
    version in the palette's dimmed text colour."""
    from qtpy.QtSvg import QSvgRenderer
    app = QApplication.instance()
    pal = app.palette() if app is not None else QPalette()
    normal = color or pal.color(QPalette.Active, QPalette.WindowText).name()
    dim = pal.color(QPalette.Disabled, QPalette.WindowText).name()
    out = QIcon()
    for mode, col in ((QIcon.Normal, normal), (QIcon.Disabled, dim)):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
               f'stroke="{col}" stroke-width="1.8" stroke-linecap="round" '
               f'stroke-linejoin="round">{_PATHS[name]}</svg>')
        renderer = QSvgRenderer(QByteArray(svg.encode()))
        for scale in (1, 2):
            pm = QPixmap(_SIZE * scale, _SIZE * scale)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            renderer.render(p, QRectF(0, 0, _SIZE * scale, _SIZE * scale))
            p.end()
            pm.setDevicePixelRatio(scale)
            out.addPixmap(pm, mode)
    return out


def attach(target, name: str) -> None:
    """Give ``target`` (an action or button) the icon ``name``, redrawn on a theme switch."""
    _attached[target] = name
    target.setIcon(icon(name))


def retint() -> None:
    """Draw every attached icon again in the palette's current colours."""
    for target, name in list(_attached.items()):
        try:
            target.setIcon(icon(name))
        except RuntimeError:            # its C++ object is gone
            pass
