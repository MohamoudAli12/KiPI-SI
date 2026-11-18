"""The boards of an Altium project (``.PrjPcb``).

A ``.PrjPcb`` is an INI file; each ``[DocumentN]`` section names one of the project's
documents with ``DocumentPath``, relative to the project and with Windows separators. A
project may hold more than one board (the board and its panel, say), so opening one asks
which. Only the standard library is needed here, so the boards are listed without the
optional reader installed.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

_SECTION = re.compile(r"^\[Document\d+\]\s*$", re.IGNORECASE)
_PATH = re.compile(r"^DocumentPath=(.*)$", re.IGNORECASE)


def is_project(path) -> bool:
    return Path(path).suffix.lower() == ".prjpcb"


def _resolve(root: Path, rel: str) -> Optional[Path]:
    """``rel`` (Windows separators) under ``root``, matching each part's case as the disk
    has it: a project saved on Windows may spell a file name differently from its file."""
    p = Path(rel.replace("\\", "/"))
    if p.is_absolute() or re.match(r"^[A-Za-z]:", rel):
        return None                     # a document outside the project; not portable
    here = root
    for part in p.parts:
        nxt = here / part
        if here.is_dir():
            # Always take the name as the directory lists it: on a case-insensitive disk
            # (macOS, Windows) ``nxt.exists()`` is true for the project's own spelling.
            names = [c.name for c in here.iterdir()]
            if part not in names:
                low = part.lower()
                nxt = next((here / n for n in names if n.lower() == low), nxt)
        here = nxt
    return here if here.is_file() else None


def project_boards(path) -> List[Path]:
    """The project's ``.PcbDoc`` files that exist, in the project's order."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
    out: List[Path] = []
    in_doc = False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("["):
            in_doc = bool(_SECTION.match(line))
            continue
        m = _PATH.match(line) if in_doc else None
        if m and m.group(1).strip().lower().endswith(".pcbdoc"):
            board = _resolve(path.parent, m.group(1).strip())
            if board is not None and board not in out:
                out.append(board)
    return out
