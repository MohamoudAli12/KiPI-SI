"""The board files KiPI-SI can open, and which source reads each.

The Open dialog's filters come from :data:`FORMATS`; a new reader (CCE) is one more entry
here.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from kipi_si.sources.base import BoardSource


@dataclass(frozen=True)
class FileFormat:
    name: str                       # for the Open dialog: "KiPI-SI snapshot"
    patterns: Tuple[str, ...]       # file name patterns, lower case: ("*.json.gz", ...)
    open: Callable[[Path], BoardSource]
    # Formats that can also be a folder: whether the folder ``path`` is one.
    folder: Optional[Callable[[Path], bool]] = None
    # Formats that can hold several boards (an Altium project): the boards in ``path``,
    # one of which is passed to ``open`` as ``board``. Fewer than two: nothing to ask.
    boards: Optional[Callable[[Path], List[Path]]] = None
    # The patterns as the Open dialog shows them, when files are named in another case
    # than ``patterns`` (Qt matches them case-sensitively on Linux); default ``patterns``.
    shown: Tuple[str, ...] = ()

    @property
    def dialog_patterns(self) -> Tuple[str, ...]:
        return self.shown or self.patterns

    def matches(self, path) -> bool:
        if Path(path).is_dir():
            return self.folder is not None and self.folder(Path(path))
        name = Path(path).name.lower()
        return any(fnmatch.fnmatch(name, p) for p in self.patterns)


def _kicad_board(path: Path) -> BoardSource:
    from kipi_si.sources.kicad_pcb.source import KiCadFileSource
    return KiCadFileSource(path)


def _odb(path: Path) -> BoardSource:
    from kipi_si.sources.odbpp.source import OdbFileSource
    return OdbFileSource(path)


def _odb_folder(path: Path) -> bool:
    return (path / "matrix" / "matrix").is_file()


def _hyp(path: Path) -> BoardSource:
    from kipi_si.sources.hyp.source import HypFileSource
    return HypFileSource(path)


def _altium(path: Path, board: Optional[Path] = None) -> BoardSource:
    from kipi_si.sources.altium.source import AltiumFileSource
    return AltiumFileSource(path, board)


def _altium_boards(path: Path) -> List[Path]:
    from kipi_si.sources.altium.project import is_project, project_boards
    return project_boards(path) if is_project(path) else []


def _snapshot(path: Path) -> BoardSource:
    from kipi_si.sources.snapshot_file import SnapshotFileSource
    return SnapshotFileSource(path)


FORMATS: List[FileFormat] = [
    FileFormat("KiCad board", ("*.kicad_pcb",), _kicad_board),
    # An unpacked job is opened by its folder, or by picking its matrix/matrix file.
    FileFormat("ODB++", ("*.zip", "*.tgz", "*.tar.gz", "matrix"), _odb, _odb_folder),
    FileFormat("HyperLynx", ("*.hyp",), _hyp),
    # Read with the optional altium-monkey package; a project opens one of its boards.
    FileFormat("Altium Designer", ("*.pcbdoc", "*.prjpcb"), _altium, boards=_altium_boards,
               shown=("*.PcbDoc", "*.PrjPcb", "*.pcbdoc", "*.prjpcb", "*.PCBDOC", "*.PRJPCB")),
    FileFormat("KiPI-SI snapshot", ("*.json.gz", "*.json"), _snapshot),
]


def format_for(path) -> Optional[FileFormat]:
    return next((f for f in FORMATS if f.matches(path)), None)


def boards_in(path) -> List[Path]:
    """The boards a file that holds several (an Altium project) has, to pick one from;
    empty for any other file."""
    fmt = format_for(path)
    return fmt.boards(Path(path)) if fmt is not None and fmt.boards is not None else []


def open_board(path, board=None) -> BoardSource:
    """The source that reads the board file ``path`` (its ``board``, one of
    :func:`boards_in`, for a file holding several); ValueError if no reader knows it, or
    the reader it needs is not installed."""
    fmt = format_for(path)
    if fmt is None:
        known = ", ".join(p for f in FORMATS for p in f.patterns)
        raise ValueError(f"KiPI-SI cannot open {Path(path).name}: it reads {known}")
    if board is not None:
        return fmt.open(Path(path), Path(board))
    return fmt.open(Path(path))


def file_filter() -> str:
    """A Qt file dialog filter: every board KiPI-SI reads, then each format."""
    every = " ".join(p for f in FORMATS for p in f.dialog_patterns)
    return ";;".join([f"Boards ({every})"] +
                     [f"{f.name} ({' '.join(f.dialog_patterns)})" for f in FORMATS])
