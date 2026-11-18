"""An Altium board (``.PcbDoc``, or one board of a ``.PrjPcb``) as a
:class:`~kipi_si.sources.base.BoardSource`."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from kipi_si.core.model.board import BoardSnapshot
from kipi_si.core.progress import NULL, ProgressReporter
from kipi_si.sources.altium.project import is_project, project_boards
from kipi_si.sources.base import BoardSource, Capabilities, ModelProvider


class AltiumFileSource(BoardSource):
    """The board in an Altium ``.PcbDoc``. Given a ``.PrjPcb``, the project's ``board`` (a
    ``.PcbDoc`` path), or its only board. Reload reads the file again, e.g. after saving it
    in Altium. Its parts' 3D models are the STEP models embedded in the file."""
    caps = Capabilities(reload=True)
    has_part_models = True

    def __init__(self, path, board=None):
        from kipi_si.sources.altium import require
        require()                       # says how to install the reader, before reading
        path = Path(path)
        self.project = path if is_project(path) else None
        if self.project is not None:
            boards = project_boards(path)
            if board is None:
                if not boards:
                    raise ValueError(f"The Altium project {path.name} lists no board "
                                     "(.PcbDoc) that exists")
                board = boards[0]
        self.path = Path(board) if board is not None else path
        self.name = self.path.name
        self.description = f"the Altium board {self.path}"

    def load(self, progress: ProgressReporter = NULL,
             refill_zones: bool = False) -> BoardSnapshot:
        from kipi_si.sources.altium.reader import read_board
        return read_board(self.path, progress)

    def files(self) -> List[Path]:
        return [self.path]

    def part_models(self, snap: BoardSnapshot) -> Optional[ModelProvider]:
        from kipi_si.sources.altium.models3d import EmbeddedModels
        return EmbeddedModels(self.path, snap.stackup.board_thickness_mm)
