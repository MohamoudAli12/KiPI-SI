# Walkthrough: your first analysis

## 1. Open your board in KiCad

Open your board in the PCB editor and click the **KiPI-SI** toolbar button. KiPI-SI opens in its
own window and reads the board through the KiCad API; the log at the bottom streams each
stage as it runs.

* **Load from KiCad** re-reads the board after you edit it in KiCad, and reloads the saved PI setup.
* **Refill zones** (on by default) refills every zone in KiCad before reading, so the zone
  fills KiPI-SI sees match your current routing. KiPI-SI analyzes filled copper only.
* **Save snapshot… / Open snapshot…** store the extracted board as a file that KiPI-SI can open
  later without KiCad. See example snapshots in the repo to experiment!
* **Power Integrity: DC / AC / Noise** and **Signal Integrity: SI** (the start of the
  toolbar, or **Ctrl+1** to **Ctrl+4**) pick the analysis mode. Sections 2 to 5 are DC, the default;
  [section 6](#6-ac-pdn-impedance) covers AC, [section 7](#7-coupled-noise) Coupled Noise and
  [section 8](#8-signal-integrity) Signal Integrity. The VRMs, series links and capacitor
  models are shared by the power modes.
* **Help** (or **F1**) opens the {doc}`user guide </getting-started/overview>` in your browser.

## 2. Pick Power Nets from Netlist

The **Board** panel on the left lists every net in the extracted design. Tick the nets you
want to analyze: only ticked nets can be simulated, and they are offered in the PI setup pin
pickers. **Power & ground only**, **All power** and **None** help pick them, and the ticks
are saved with the setup.

Below that are the **Copper layers**, the **Display** options (color by layer or net, Z
scale, vias, pads, mask, silkscreen, part **3D Models**), and **PI Models**, which marks the
parts of the current analysis in 3D. Clicking a part in 3D selects it in the setup, and the
**Info** box shows whatever you last clicked, with **Select in KiCad** to find it in the PCB
editor.

![PI Models marking the parts of the analysis, snapped to the selected +3.3V switcher](/images/pi_models.png)

The **Power tree** tab, beside the 3D view (or **Ctrl+T**), shows a block diagram of the
modelled power network, left to right in the direction power flows. Drag to pan, use the
wheel or **Zoom in** / **Zoom out** to zoom, **Fit** to see it all, and save it as a PNG.

![The power tree of the multiphase buck example: a 12 V source, the 4-phase switcher, the 0.9 V core rail, its load and capacitor models](/images/power_tree.png)

The **Stackup** toolbar button lists every copper and dielectric layer with its thickness,
material, εr, thermal conductivity and resistivity, with a cross-section drawn to scale.
Untick **Lock to imported values** to try other thicknesses and materials: every analysis
uses the edited stackup.

![The Stackup window: copper and dielectric layers with thickness, material, εr, thermal conductivity and resistivity](/images/stackup.png)

Drag to rotate, scroll to zoom and shift-drag (or middle-drag) to pan; the
{ref}`user guide <keys>` lists every keyboard shortcut.

## 3. Model the Power Distribution System

The **PI setup** panel on the right holds the power tree. Each list has **Add**,
**Duplicate** and **Remove** buttons, and every field has a tooltip. Pins are chosen with a
picker: the net, then the part, then optionally the pin numbers. As you pick pins, KiPI-SI
pre-fills what usually follows from them (a VRM's target voltage from the net name, ground
pins, a series link's other side and a resistor's value), and problems are shown in red.
**Import…** fills the power tree from a Tomachie power-tree file (`<design>.pdn.json`).

**VRMs tab**: one entry per regulator, power input, or ideal supply. A VRM is a **Source**,
**LDO**, **Switcher** or **Isolated** converter, with its output pins and target voltage,
its input pins (which link it to the rail upstream), efficiency or quiescent current, and
optional remote sense, ground pins, load line, dropout, input range, DC accuracy, current
limit and multiple **Phases**. KiPI-SI works out each VRM's input current from what it feeds.

To try it without a design of your own, open the example board in
[`examples/multiphase_buck`](https://github.com/MohamoudAli12/KiPI-SI/blob/main/examples/multiphase_buck): a 4-phase 12 V → 0.9 V, 40 A core rail
(`python -m kipi_si --snapshot examples/multiphase_buck/multiphase_buck.kipi_si.json.gz`).

**Loads tab**: one entry per consumer: its **Supply pins**, **Current** (split evenly or by
pin group), optional **Ground pins** and a **Tolerance** for PASS/FAIL. **Load models**
(**Model ▾**) save and apply a part's supplies as a YAML file.

![Load editor](/images/setup_loads.png)

**Series links tab**: parts that pass DC from one net to another, such as sense
resistors, ferrite beads, fuses, load switches and 0 Ω links: **Side A pins**, **Side B
pins** and a **Resistance**. **Import SPICE model…** uses the maker's SPICE model of the part
for both DC and AC, including diodes and multi-pin parts such as common-mode chokes.
**In order to assign a series link, the nets on either side must both be defined as power
nets in the net selection pane.**

**Solve tab**: every combined rail, with a checkbox. Untick the rails that are not modeled or
routed yet to solve the rest.

![The Solve tab: tick the net groups to solve](/images/dc_solve_tab.png)

**Mesh tab**: **Max edge** is the largest FEA mesh triangle edge in mm; smaller is more
accurate and slower. **Via plating** sets each kind of via's plating thickness and fill.

![The Mesh tab with the via plating rules](/images/setup_mesh.png)

**Thermal tab** (off by default): tick **Electro-thermal co-simulation** to make losses heat
the board and the warmer copper become more resistive. Each copper layer has its own
temperature, with heat crossing the laminate and running down vias. Inspired by
[KiCad Thermal Sim](https://github.com/PoeAlex/KiCad_Thermal_Sim) by
[PoeAlex](https://github.com/PoeAlex).

![Thermal settings](/images/setup_thermal.png)

The setup is saved as `<board>.kipi_si-setup.yml` next to the board when you click **Save** and
every time you solve. It travels with the project and can go into version control. AI agents
can make quick work of power tree modelling by editing this file directly.

## 4. Solve

Click **Solve all**. Every rail is meshed and solved, downstream loads first, so each VRM's
input current includes everything it feeds. Progress streams into the log; **Cancel** stops
the run.

Click **Report** to write an HTML report next to the board, or choose **PDF**. The HTML
report is a single portable file with the summary and every results table, an interactive 3D
view per rail, per-layer voltage and current-density maps, the board temperature map when
thermal is on, and a **User notes** box.

| Summary tables | Interactive 3D per net group |
|---|---|
| ![Report summary tables](/images/report_tables.png) | ![Report 3D voltage view](/images/report_3d.png) |

## 5. Read the results

In the **Results** pane, choose a **net group** and a **field** to show in 3D: **Voltage**,
**Current density** (tick **Arrows** to see the flow), **Power density**, **Via current**
or **Temperature**. Click any point to probe it in the Info box, and set the **Color
scale** to look closer.

![Voltage drop along the +12V input plane, from the input connector to the two loads, with the Loads results table](/images/voltage.png)

![Current density with flow arrows through the +12V input path and the U201 eFuse, with the Series links table](/images/current_density.png)

| Via current | Temperature |
|---|---|
| ![Via current, with the Vias table ranked by current](/images/via_current.png) | ![Board temperature from the electro-thermal solve, with the Thermal results tab](/images/temperature.png) |

The result tabs give **Loads** (effective voltage, drop and PASS/FAIL), **VRMs**, **Series
links** (I²R losses), **Vias** ranked by current, **Losses**, **Thermal** and **Notes**.
**Export ▾** writes CSV or ParaView files, and **Save results…** writes a results file that
**Open results…** reloads without solving again.

## 6. AC: PDN impedance

Switch **Mode** to **AC**. The **AC setup** shares the VRMs and series links with DC mode and
adds:

* **Capacitors tab**: RLC models (capacitance, ESL, ESR) for the decoupling capacitors, each
  shared by a group of identical parts, or the maker's SPICE model. **Models from values**
  starts one model per capacitor value. Models can be derated for DC bias, temperature,
  aging and tolerance. **Important**: model capacitors of the same value in different case
  sizes separately.
* **Probes tab**: where to plot the PDN impedance, usually a device's supply and ground pins,
  each with a **flat** or **custom** target. The **Target Impedance/Frequency Calculator**
  works out a flat target from the device's voltage tolerance and load step, following Smith
  et al., ["Power Distribution System Design Methodology and Capacitor Selection for Modern
  CMOS Technology"](https://doi.org/10.1109/6040.784476), IEEE Trans. Adv. Packaging, 1999.
  Targets apply above the VRM's **Control loop bandwidth**.
* **Sweep tab**: frequency range and resolution, and the capacitor deratings.
* **Mesh tab**: mesh size and minimum edge at plated holes.

| Capacitor models | Target calculator |
|---|---|
| ![Capacitors tab](/images/ac_capacitors.png) | ![Target impedance calculator](/images/ac_target_calc.png) |

Pick the **Rail** and **Ground** and click **Solve rail**. The rail's copper and its ground
are field-solved, so plane resistance, spreading inductance, plane capacitance, cavity
resonances and via inductance all come from the layout; the capacitors and series links are
attached at every frequency. The VRM is not modeled as an impedance (the open-loop PDN).
**Important:** AC analysis is a massive compute problem. Many probes and a finer mesh
increase simulation time dramatically.

The **Impedance** tab plots |Z| against frequency for every probe, with its target, and a
cursor to read values. The **Board map** tab shows the mesh, probes and capacitors, and the
**Transient** tab estimates each probe's undershoot and overshoot for its load step.
**Report**, **Export CSV…** and **Save results…** work as in DC mode.

![The Board map of the core rail's solve: the VCORE and GND mesh, the probe and the capacitors by model](/images/ac_board_map.png)

![The impedance plot of the example's 0.9 V core rail against its custom target, with the cursor on the anti-resonance and its values in the Info box](/images/ac_impedance.png)

## 7. Coupled Noise

Switch **Mode** to **Noise**. The **Coupled Noise setup** treats one of the setup's
**Switcher** VRMs as an *aggressor* and the signal nets you name as *victims*. The
screenshots below are the `examples/validation/coupled_noise` example: a 12 V to 1.8 V,
1 MHz buck over a ground plane, with three victims. Open its snapshot to try it.

* **Aggressors tab**: **Add** makes an aggressor from a switcher VRM and fills it in from the
  board: the switching device, inductor, switch node and capacitors. Give the switching
  frequency and edge times; datasheet values such as Coss and Qrr are optional. KiPI-SI traces
  each capacitor's hot loop through the copper for its inductance and its coupling.
* **Victims tab**: each victim is a net with its driver and receiver pins and a **Type**
  (CMOS, open drain, terminated, LVDS, analog input or undriven) and **Logic level**, which
  set its loading and noise margin.
* **Capacitors tab**: the same capacitor models as AC mode.
* **Settings tab**: harmonics, damping, victim resolution and the **Board model**, the slow
  but more accurate field model of the converter's copper (untick it for a quick look).

Pick the **Aggressor** and click **Solve**. Tick **Scan nearby nets** to also check every
signal net near the aggressor. The **Waveforms** tab plots the switch node with its ringing,
the inductor and capacitor currents and the rail ripple, in time or as a spectrum.

![The Waveforms tab: the buck's switch node over two periods, ringing at 179 MHz on each hard rising edge while the soft falling edge settles at once](/images/noise_waveforms.png)

The **Results** table lists each victim's peak noise at its receiver, its margin, the
dominant mechanism and PASS or FAIL. **Victim noise** plots the noise, as a whole or by
mechanism (capacitive, inductive, common ground).

![Victim noise for SIG_SW: the superposition at the receiver with its capacitive and inductive parts, and the results table](/images/noise_victim.png)

**Victim held high and low** draws the noise riding on the receiver's high and low levels
against its thresholds.

![SIG_SW held high and low, with the noise riding on each level](/images/noise_states.png)

**Coupling in 3D** colors the selected victim's traces by their share of the peak noise, so
the pieces to move stand out. **Hot loops in 3D** draws the capacitor loops' current, and
**Fields in 3D** the H and E fields over the board, with near-field hotspots and a first
radiated estimate against CISPR 32 class B. Victims crossing a split in their reference
plane are noted.

![Coupling in 3D for SIG_LOOP: the victim colored by its share of the 631 mV peak, beside the capacitor loops](/images/noise_coupling_3d.png)

The mechanisms point to different fixes: capacitive noise comes from the switch node's
dV/dt, inductive noise from the hot loop's dI/dt and common noise from the switching
current's return. **Report** and **Save results…** work as in the other modes.

## 8. Signal Integrity

Switch **Mode** to **SI** (**Ctrl+4**). The **Signal Integrity setup** has four tabs. To
try it, open `examples/signal_integrity/signal_integrity.kipi_si.json.gz`: a clock net through
a series resistor and a USB pair changing layers through vias, with a channel set up for
each.

* **Quick Scan**: **Scan** cuts every signal net (or only the nets ticked in **Board**) into
  short sections and field-solves each cross-section with its neighbours. Each net gets
  PASS, WARN or FAIL for its impedance (Z0, or Zdiff for pairs found by name: `_P`/`_N`,
  `+`/`-`, `DP`/`DM`), its worst crosstalk coefficient, any length with no reference plane
  or crossing a plane's gap, layer changes without a return via nearby, via stubs that
  resonate in band, and pair skew. **Impedance in 3D** colors the traces by how far they
  are from target. **Make a channel** turns the selected net into a channel. Slow control
  nets (enables, resets, LEDs, I²C, JTAG) are left out unless **Slow nets** is ticked. Cuts
  that come out alike are solved once, in parallel on the CPU's cores: a 6-layer board with
  about 400 signal nets takes a few minutes, and a rescan seconds.
* **Channels**: a channel is a net or a pair, followed through series resistors and
  AC-coupling capacitors to its receiver. **Add bus…** makes one for each net between a
  transmitter and a receiver part (a DDR byte lane, an ADC's lanes), with the neighbours as
  aggressors. Pick its **Interface** (rate, swing, edges,
  terminations, equaliser and limits come from it, and any can be overridden) and its
  **buffers**: generic ones, or a model from a manufacturer's **IBIS** file at a corner.
  **Aggressors** add their near- and far-end crosstalk.
* **Results**: after **Solve**, the checks (impedance, insertion and return loss at
  Nyquist, mode conversion, skew, the eye against the receiver mask, COM, overshoot,
  ringback, monotonic edges, crosstalk) and the **SI plots** tab: the eye (statistical at
  the target BER with the best equaliser, or the raw or PRBS eye), TDR, S-parameters,
  waveforms at the dies and the pulse response. **Export Touchstone…** writes the channel's
  `.s2p`/`.s4p`, and **Export SPICE…** a passive rational model of it as a SPICE subcircuit
for any circuit simulator; **Report** and **Save results…** work as in the other modes.
* **Settings**: section length, etch, copper roughness (Hammerstad, Groisse or Huray), the
  sweep and the scan's limits.

## Tips and troubleshooting

* **A load shows DISCONNECTED** usually means unrouted copper, an unfilled zone, or a
  missing series link for a part between two power nets.
* **Unexpected voltage drop:** thermal reliefs, necked traces, via counts and anti-pads in
  planes dominate DC drop; the Current density view with Arrows shows the bottleneck.
* **Slow solves:** raise **Max edge**, or analyze fewer nets at a time. On Intel x86, install
  the PARDISO solver (above).
* **"KiPI-SI works with one KiCad at a time"** although only one is open: a KiCad that did not
  exit cleanly may still be running; end it in the task manager.
* **Logs:** each session writes to `kipi_si/kipi_si-<date>-<time>-<pid>.log` in the temporary
  folder, with a matching `.crash.log`. Attach both, and **About → Copy version info**, to
  bug reports. The {doc}`user guide </getting-started/overview>` has more troubleshooting.
* **Have Fun:** The author asks that you share what projects this package has simulated, and what power integrity issues you have found with it. Conductor simulation gives incredible insight into how PCBs actually function in practice. See what happens when you pump 10 amps into a 5 mil trace with the temperature results view.
