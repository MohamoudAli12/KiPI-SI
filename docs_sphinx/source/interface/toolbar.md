(toolbar)=
# Toolbar

## Every toolbar button

```{list-table}
:header-rows: 1
:class: kipi-table

* - Button
  - What it does
* - **Load from KiCad** plugin
  - Re-reads the board from the running PCB editor (after you change the layout) and reloads the saved setup. The nets you have ticked stay ticked. Save the setup first if you have unsaved changes. Only one KiCad may be open (see {ref}`Starting KiPI-SI <window>`).
* - **Refill zones** plugin
  - When ticked, KiPI-SI asks KiCad to refill every zone and waits for it before reading. KiPI-SI only sees *filled* copper, so leave this on unless the fills are already current and the refill is slow.
* - **Open snapshot…** plugin
  - Opens a board saved with **Save snapshot…**. KiCad does not need to be running.
* - **Open…** standalone
  - Opens a board file: a KiCad board (`.kicad_pcb`), an ODB++ job (`.zip`, `.tgz`, or its `matrix/matrix` file), a HyperLynx file (`.hyp`) or a KiPI-SI snapshot (`.kipi_si.json.gz`). Its saved setup comes with it, as with **Load from KiCad**. The arrow beside it lists the boards opened lately.
* - **Reload** standalone
  - Reads the open board file again. When the file is saved (in KiCad, say), KiPI-SI asks whether to read it again by itself. Ticked nets stay ticked.
* - **Save snapshot…**
  - Saves the extracted board as `.kipi_si.json.gz`, to analyze later, on another machine, or to attach to a bug report.
* - **Top / Bottom / Iso**
  - Snap the 3D camera to look down on the board, up at its underside, or from an isometric angle (keys **Z**, **Shift+Z** and **Home**; see {ref}`Keyboard shortcuts <keys>`). They also bring the 3D view to the front from the Impedance and Board map tabs.
* - **Screenshot…**
  - Saves whatever is in the middle as a PNG: the 3D view, the impedance plot or the board map, whichever tab is showing.
* - **Open results…**
  - Reopens saved results without solving again. Load the same board first. In DC mode it opens a DC solve saved with **Export ▾ → Save results…**; in AC mode, the rails saved with the AC panel's **Save results…**.
* - **Stackup**
  - Opens the {ref}`Stackup window <stackup>`: the board's layers with their thicknesses, εr and copper resistivity.
* - **Power tree**
  - Opens a block diagram of the setup, drawn left to right in the direction power flows: each source and regulator, the rails they drive, series links between rails, and the loads and capacitor models on each rail (capacitors are grouped per model and rail, with a dashed line). VRM types differ in colour and tag: a **SOURCE** has a double border, and regulators (**LDO** and **SMPS**) a dashed one. A rail with three or more loads, or capacitor groups, packs them into a framed grid fed by one arrow, titled with their count (and the loads' total current); the grids take the shape that lets the whole tree fit the window largest. Each block sits just right of the one feeding it. Ground nets, and net ties between them, are left out. Hover a block for its pins; drag to pan, {kbd}`Ctrl` + wheel to zoom, **Save image…** for a PNG. It redraws as the setup changes.
* - **Help** {kbd}`F1`
  - Opens this guide in your web browser.
* - **About**
  - Version, author and project links, and how often the project has been cloned and its releases downloaded. Those counts are fetched once a session from the project's GitHub repository; offline, the last ones fetched are shown, or none. **Copy version info** copies the versions of KiPI-SI, Python, its libraries and the sparse solver in use, for bug reports. **Check for updates** asks GitHub for the newest KiPI-SI release and says whether it is newer than yours, with a link to download it; KiPI-SI never checks on its own. In standalone KiPI-SI started by its launcher, **Manage dependencies…** closes KiPI-SI and opens its setup (for example to add or remove PARDISO).
* - **Power Integrity: DC / AC / Noise Signal Integrity: SI**
  - Chooses the analysis, at the start of the toolbar (**Ctrl+1** to **Ctrl+4**). The setup dock shows that mode's panel; **Import…**, {ref}`Auto-fill power tree… <tree-autofill>` and {ref}`Auto-fill rail… <rail-autofill>` fill the power tree, so they are in the Power Integrity modes only. The DC setup and results are kept while you are in AC and come back when you switch to DC. You cannot switch while a task is running.
```
