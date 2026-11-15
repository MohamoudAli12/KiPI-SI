(board-panel)=
# Board panel

The left-hand dock. Its four parts are separated by splitters you can drag.

(nets)=
## Nets

Every net on the board. **Tick the nets you want to analyze.** Ticked nets are drawn in 3D and are the only nets offered in the setup's pin pickers, so a net you need for a VRM, load, series link, capacitor or probe must be ticked first.

```{list-table}
:header-rows: 1
:class: kipi-table

* - Control
  - What it does
* - Filter box
  - Shows only nets whose name contains the text.
* - **Power & ground only**
  - Hides signal nets that are not ticked. Power nets are shown in orange with `[PWR]`, grounds in blue with `[GND]`. KiPI-SI recognizes them by name (`+3V3`, `VCC`, `GND`…), net class, or a zone with several pads.
* - **All power**
  - Ticks every power and ground net, keeping any others already ticked.
* - **None**
  - Unticks everything.
* - Selecting nets
  - Click a net (Ctrl or Shift for more) to pick it out in 3D: every other net is dimmed and the selected nets are drawn in full color over everything, so you can follow them under planes and on other layers. **Esc** in the list clears the selection. In SI mode, the selected Quick Scan net, or the selected channel with its series nets and aggressors, is picked out the same way. **Dim other nets** (Display) turns this off.
```

The ticked nets are saved with the setup. A board with no saved choice starts with a guess: its largest power planes and the main ground. Building the 3D copper of a big net takes a moment; nets appear as they finish, and **Cancel** stops the build.

(layers)=
## Copper layers

Each copper layer with its thickness and height in the stackup. Untick a layer to hide it; **All** and **None** show or hide every layer at once. Hiding layers does not change the result colors; set the {ref}`color scale <color-scale>` to look closer.

(display)=
## Display

(pi-models)=
```{list-table}
:header-rows: 1
:class: kipi-table

* - Control
  - What it does
* - **Color**
  - Colors the plain copper by layer or by net. By layer, each layer has its color from the PCB editor's color theme (*Preferences → Colors* in KiCad), read again on every **Load from KiCad**; the log names the theme. If the theme cannot be read, KiCad's default theme colors are used.
* - **Z scale**
  - Stretches the stackup vertically (1× to 100×) so the layers can be told apart. It starts at 1×, the board's true proportions. It only changes the drawing.
* - **Opacity**
  - How solid the copper layers and pads are drawn, from 5% to 100%, in both the plain and the result views. Lower it to see the layers beneath; vias stay solid.
* - **Vias / Pads / Board**
  - Show or hide via barrels, pads and the board body.
* - **Mask / Silkscreen**
  - Show the solder masks, in their color and open over the pads, and what the silkscreens print: the board's drawings and text on F.SilkS and B.SilkS, off the pads. Text read from a board file is drawn in a font like KiCad's, in the same place; the running KiCad and ODB++ give KiCad's own. Both start off, since they hide the copper. The copper and result views each remember these settings, like 3D Models: over results they start off, whatever the copper view shows.
* - **PI Models**
  - Marks the parts the current analysis uses on the copper: a dot on each of their pads, larger on the rail's pins and smaller on ground, with the part's name above. In DC mode those are the setup's **VRMs** (green), **loads** (cyan) and **series links** (magenta). In AC mode the **probes** (violet) take the loads' place — the impedance is looked into at a probe, and a load's current says nothing about it — beside the same VRMs and series links and the **capacitors** with a model (white), which only an impedance sweep uses. Only pads on a net shown are marked, and the marks follow setup edits. They are drawn over the plain copper only, not over results. Unticked to start with.  Clicking a VRM, load, series link, probe or capacitor model in the setup's lists marks it (every part of a capacitor model) in **amber**, and with {ref}`Snap to selected <pi-models>` ticked brings the view to it; PI Models is left as you set it. Clicking a part's name (or one of its dots) in 3D selects it in the current mode's setup, ready to edit. Either way, the newly selected part blinks red and amber for a few seconds. Clicking a capacitor in 3D selects its model in AC mode's Capacitors tab.
* - **Snap to selected**
  - Brings the view to a part when it is picked in the setup's lists (ticked to start with). Available only while PI Models is ticked, since it goes to the part's marks. Untick it to keep the view where it is; the part is still marked and blinks. KiPI-SI remembers the choice.
* - **3D Models**
  - Shows the KiCad 3D models of every part on the board. They start hidden, so a board opens without waiting for them; tick **3D Models** to load and show them. The geometry and the result views each keep their own setting. See {ref}`Part 3D models <part-models>` below.
* - **Guess models**
  - Picks models from KiCad's library for the parts that have none, by footprint name, and ticks **3D Models**. Only when clicked; see {ref}`Part 3D models <part-models>`.
```

```{figure} /images/pi_models.png
:alt: PI Models marks on the board, the selected switcher in amber

PI Models, snapped to the selected +3.3V switcher.
```

(part-models)=
### Part 3D models

- KiPI-SI asks KiCad's command-line tool, `kicad-cli`, to export just the parts it needs, so KiCad finds the model files the same way its own 3D viewer does (STEP and VRML). It runs in the background, the first time the models are shown; each part is read once per board.
- `kicad-cli` reads the **saved** `.kicad_pcb` file. A part moved since the last save is drawn where it was saved; save the board and click **Load from KiCad** to update it.
- The **Z scale** stretches the board but not the parts: top-side parts sit on the stretched board at their true height, and on a board made thicker or thinner in the {ref}`Stackup window <stackup>`.
- Clicks go through the models to the copper beneath, so probing works as without them.
- A part whose model KiCad cannot find is named in the log with the missing path. If `kicad-cli` or the board file cannot be found, the log says so once and no models are drawn; see {ref}`Troubleshooting <ts-models>`.
- **Guess models** is for a board with no KiCad board file to read models from (an ODB++ job, a snapshot opened away from its board) and for parts whose models KiCad cannot find. For each part with no model, it looks up the footprint (or ODB++ package) name in the 3D model library KiCad installs: the whole name, a name the part's ends with (`Capacitor_SMD_C_0402_1005Metric`), the name it starts with (a `_HandSolder` variant), a chip resistor, capacitor or inductor's size code (`CAPC1005X55N`, `C0402`, `R0805`), and last the closest name. `kicad-cli` then places the models where the parts sit, turned and on their side. It is a guess, so it never runs by itself: a model not found by the whole name is left out if it is far larger or smaller than the part's pads, and the log names each one kept. Opening or reloading the board drops them.
- Standalone, part models are offered when KiCad is installed on the computer.

(info)=
## Info and Select in KiCad

Shows a summary of the board when it loads, and afterwards whatever you last clicked in 3D: the layer and coordinates, the pad or via hit (net, drill, layer span), and, when results are shown, the voltage, drop, current density, power density and via current at that point. In AC mode it shows the impedance plot's cursor values.

The summary says where the board came from (for example *From KiCad PCB editor 10.0.7*, and the snapshot file it was opened from). Under **Placeholders** it lists anything KiPI-SI had to fill in because the source did not give it, such as a default stackup when the board's own is incomplete. Results that depend on a placeholder are only as good as the placeholder.

**Select in KiCad** selects the picked pad or via in the PCB editor, so you can find it in your layout. It needs a live KiCad connection (not a snapshot), so the plugin has it and standalone KiPI-SI does not.
