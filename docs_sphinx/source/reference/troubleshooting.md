(troubleshooting)=
# Troubleshooting

## The KiPI-SI button does not appear in KiCad

Enable **Preferences → Plugins → Enable KiCad API** and restart the PCB editor. The first start builds a Python environment and downloads a few hundred MB, which can take several minutes. If the button never appears, right-click the action in *Preferences → Plugins* and choose *Recreate Plugin Environment*. On macOS, select a Python 3.10–3.13 interpreter there.

(ts-multiple-kicad)=
## "KiPI-SI works with one KiCad at a time"

More than one KiCad project manager or standalone PCB editor is open, and KiPI-SI cannot tell which one holds your board. Close the others (the message lists them with their process IDs) and start KiPI-SI again from the PCB editor of the board you want. If you know the check is wrong, set the environment variable `KIPI_SI_ALLOW_MULTIPLE_KICAD=1` to skip it. If the running programs cannot be listed, KiPI-SI carries on.

(ts-launcher)=
## Standalone KiPI-SI does not set up or start

- **No suitable Python:** the launcher needs Python 3.10 to 3.13 and names the ones it found. Install one from python.org (on Linux, also `python3-venv`).
- **The setup failed:** the message says why, and the launcher's log (in `logs` next to KiPI-SI's environment) has everything the installer printed. Check the network connection and free disk space, then start the launcher again; it picks up where it stopped. `python kipi_si_launcher.py --repair` starts over.
- **A message box says to use a terminal:** that Python has no tkinter for the setup window. Run `python kipi_si_launcher.py` in a terminal and answer there.

(ts-kicad-file)=
## A KiCad board file opens with copper missing, or not at all

- **Zones have no copper:** they were saved unfilled, and KiPI-SI does not fill zones. Fill them in KiCad (**B**), save, and **Reload**. The board summary lists unfilled zones under **Placeholders**.
- **Copper looks out of date:** KiCad fills zones when asked, not on every edit. Refill and save in KiCad after moving copper.
- **"saved by KiCad 6 or older":** open the board in KiCad 7 or later, save it, and open it again.

(ts-odbpp)=
## An ODB++ job opens with nets or copper missing

- **"not an ODB++ job":** the archive has no `matrix/matrix` file, e.g. a zip of Gerbers. Export ODB++ from the design tool.
- **"no netlist":** the job has no `eda/data`; export it with its netlist, or KiPI-SI cannot tell which copper is which net.
- **A net from KiCad has a different name:** KiCad's ODB++ export writes spaces in net names as underscores. Pick the net again in the setup.
- **A copper drawing carries no current:** some exporters (KiCad among them) do not say which net drawn copper is on. KiPI-SI gives it the net of the copper it touches; on its own it has none.

(ts-hyp)=
## A HyperLynx file does not open, or opens with parts missing

- **"not a HyperLynx board file":** the file has no `BOARD`, `STACKUP` or `NET` records. Export it again as a board.
- **"ends inside a block":** the file was cut short, e.g. copied while it was still being written. Export it again.
- **A part is missing or off its place:** a part with no pads on any net is not in the file, and a part is drawn in the middle of its pads because the file does not say where it sits.
- **"pad stacks are used but not in the file":** those pads are read with no copper. Export the file again from the design tool.

## Clicking the KiPI-SI button does not open a new window

KiPI-SI is already open, perhaps minimized or behind KiCad; the button brings it to the front. If it is not open and still does not start, check the session log for a stale lock and delete `kipi_si-<user>.lock` (`kipi_si-standalone-<user>.lock` for standalone KiPI-SI) from the temporary folder.

(ts-models)=
## No part models are drawn

- Check **3D Models** is ticked in {ref}`Display <display>`. It starts unticked.
- The log says why. KiPI-SI needs KiCad's `kicad-cli`: it looks in the connected KiCad, the PATH, the usual install folders and a Flatpak KiCad. Otherwise set the environment variable `KIPI_SI_KICAD_CLI` to its full path.
- It also needs the board's `.kicad_pcb` on disk, next to the project or the snapshot. A snapshot opened on another machine usually has none, nor does an ODB++ job: click {ref}`Guess models <pi-models>` to pick models from KiCad's library by footprint name. It needs KiCad's 3D model library installed; if it is somewhere KiPI-SI does not look, set `KICAD10_3DMODEL_DIR` (or your KiCad version's) to it.
- A part whose model file KiCad cannot find is named in the log with the missing path; KiCad's own 3D viewer shows the same gap. Fix the path in the footprint's 3D model settings and save the board.

## A net is missing from the pin pickers

Pickers only offer nets ticked in the {ref}`Nets <nets>` list. Tick it (untick **Power & ground only** or use the filter to find a signal net).

(ts-no-path)=
## Loads not connected by copper

Before solving, KiPI-SI checks that every load pin has a path to its VRM through copper or {ref}`series links <dc-links>`, and its ground pins to the ground reference. A pin without one draws nothing, and the Notes tab lists it:

- Some pins of a load unconnected: its current is drawn through its other pins. A pin group with no pin connected draws nothing.
- No supply pin, or no ground pin, connected: the load's current is left out of the solve and it shows as **DISCONNECTED**.
- A rail where no load is connected at all: the solve stops with **Cannot solve**. So does an unconnected VRM pin.

The cause is usually unrouted copper, an unfilled zone (keep **Refill zones** on), or a part in series that needs a series link. Show the net in 3D and look for the gap.

## The drop is larger than expected

Thermal reliefs, necked traces and too few vias dominate DC drop. Use **Current density** with **Arrows**, and the Vias table sorted by current. Compare the 3D copper with KiCad: KiPI-SI only sees filled copper.

## NOT CONVERGED

The iterative solver did not reach its tolerance on a very large group. Raise **Max edge** to shrink the problem, or install the optional PARDISO solver (see the README) for a direct solve of up to 1M unknowns.

## Solves are slow

Raise **Max edge**, analyze fewer nets at once, and untick unneeded groups in the Solve tab. In AC, lower **Field solves per decade**, raise **Min edge**, or check that **Grade only near the rail** is ticked. Large planes are cheap; long fine traces are not. PARDISO helps a lot on large boards (Windows and Linux, x86-64).

## An AC curve looks wrong

- Check the notes for capacitors left out for having no model.
- Check every model's ESL and ESR units (nH and mΩ).
- Check the probe's ground pins are on the ground being simulated.
- Remember the VRM is not modeled: the low-frequency rise is expected.
- Raise **Points per decade** if resonances look jagged: around them the copper is solved at every point of the sweep.

## Reporting a bug

Open an issue at [github.com/MohamoudAli12/KiPI-SI/issues](https://github.com/MohamoudAli12/KiPI-SI/issues). Attach the session's `.log` and `.crash.log`, the text from **About → Copy version info**, and if you can, a board snapshot and setup file that show the problem.
