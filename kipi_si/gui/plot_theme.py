"""The plots' colours, dark or light with the windows' theme (:mod:`kipi_si.gui.theme`).

The plots beside the 3D view (PI plots, impedance, transient, AC board map, Coupled Noise
waveforms, SI plots) draw with :func:`ink`, the shown theme's colours, and the curves with
:data:`SERIES`. :func:`use` switches the theme before the windows' palette changes; each
plot (:class:`FollowsTheme`) then draws itself again. The reports keep their own light
colours whatever the windows show.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from qtpy.QtCore import QEvent


@dataclass(frozen=True)
class PlotTheme:
    dark: bool
    bg: str              # the figure and its axes
    fg: str              # tick labels and axis labels
    title: str           # titles and legend text
    spine: str           # the axes' frame
    faint: str           # reference lines (a target, a bandwidth, Nyquist)
    zero: str            # the zero line
    grid: str
    grid_major: str      # on a log axis, with a minor grid
    grid_minor: str
    panel: str           # a legend's or a hover label's box
    edge: str            # its edge
    muted: str           # quiet text drawn on the plot
    cursor: str          # the impedance cursor's cross-hair
    marker: str          # a plain marker (a part with no model)
    probe_text: str      # a probe's name on the board map
    series: Tuple[str, ...]


DARK = PlotTheme(
    dark=True, bg="#1e1e1e", fg="#cccccc", title="#dddddd", spine="#888888",
    faint="#888888", zero="#666666", grid="#444444", grid_major="#555555",
    grid_minor="#333333", panel="#2a2a2a", edge="#555555", muted="#aaaaaa",
    cursor="#e8e8e8", marker="#f0f0f0", probe_text="#ffb0b0",
    series=("#4fa3ff", "#ffa040", "#60d060", "#ff6080", "#c080ff", "#40d0d0", "#e0e060"))

# The same hues, deep enough to read on white.
LIGHT = PlotTheme(
    dark=False, bg="#ffffff", fg="#333333", title="#222222", spine="#777777",
    faint="#777777", zero="#999999", grid="#dddddd", grid_major="#cccccc",
    grid_minor="#eeeeee", panel="#ffffff", edge="#bbbbbb", muted="#666666",
    cursor="#333333", marker="#222222", probe_text="#b00000",
    series=("#1f77b4", "#e07000", "#2ca02c", "#d62750", "#8a4fd0", "#119c9c", "#9a9a00"))

_shown = DARK

#: The curves' colours in the shown theme. One list, changed in place by :func:`use`, so
#: every module that imported it (as ``COLORS``) draws in the shown theme's.
SERIES: List[str] = list(DARK.series)


def ink() -> PlotTheme:
    """The shown theme's plot colours."""
    return _shown


def use(dark: bool) -> None:
    """Draw plots dark or light from now on (the plots on screen redraw on the palette
    change that follows: :class:`FollowsTheme`)."""
    global _shown
    _shown = DARK if dark else LIGHT
    SERIES[:] = _shown.series


def style_axes(ax, grid: bool = False) -> None:
    """``ax`` in the shown theme: its face, frame, ticks, labels and title (and a grid)."""
    t = _shown
    ax.set_facecolor(t.bg)
    for s in ax.spines.values():
        s.set_color(t.spine)
    ax.tick_params(colors=t.fg, which="both")
    ax.xaxis.label.set_color(t.fg)
    ax.yaxis.label.set_color(t.fg)
    ax.title.set_color(t.title)
    if grid:
        ax.grid(True, color=t.grid, lw=0.5)


def legend(ax, **kw):
    """``ax``'s legend in the shown theme; None when it has nothing to list."""
    if not ax.get_legend_handles_labels()[0]:
        return None
    t = _shown
    kw.setdefault("fontsize", 8)
    leg = ax.legend(facecolor=t.panel, edgecolor=t.edge, **kw)
    for txt in leg.get_texts():
        txt.set_color(t.title)
    return leg


class FollowsTheme:
    """For a plot widget with a ``figure``: on a switch of theme, its figure takes the new
    background and :meth:`retheme` draws it again. Put before QWidget in the bases."""

    def changeEvent(self, event):
        if event.type() in (QEvent.PaletteChange, QEvent.ApplicationPaletteChange):
            if getattr(self, "_drawn_in", DARK) is not _shown:
                self._drawn_in = _shown
                self.figure.patch.set_facecolor(_shown.bg)
                self.retheme()
        super().changeEvent(event)

    def retheme(self):
        """Draw the plot again in the shown theme."""
        raise NotImplementedError
