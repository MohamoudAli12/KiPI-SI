(si-setup)=
# Signal Integrity setup tabs

The top of the panel picks the **Channel** to show; it is also the one selected in **Channels**. What a channel still needs is listed under it. **Solve** is at the foot of the channel's settings, so a channel is set up and solved in one place; **Ctrl+Return** solves it from any tab.

To solve several channels at once, tick them in the **Channels** list (or **Tick all**): Solve becomes **Solve N ticked** and solves them one after another, on the board indexed once. Each result shows as it finishes, and each channel's row says PASS, WARN, FAIL or ERROR; pick a channel to see its checks and plots. **Cancel** stops between channels and keeps the ones done. With nothing ticked, Solve solves the channel picked. The ticks are saved with the setup.

In SI mode the **Nets** list in **Board** lists signal nets, not power: pairs first, then single nets, then slow control nets (greyed), then ground and power, each tagged. It keeps its own ticks, apart from the PI modes'. These start as the channels' nets and their aggressors, or every pair when there are no channels yet. **Signal nets only** hides the ground and power nets, and **All pairs** ticks every pair. The sections (**Differential pairs**, **Single-ended**, **Ground and power**) fold with a click on their header; the grip under the list drags it taller, and the panel then scrolls (a double-click on the grip shrinks it back). Pairs are found by name; where a name misleads, select the nets and right-click: **Make a differential pair** (two nets, the first selected the positive leg), **Make single-ended**, or **Back to automatic**. The nets set so are tagged *set*; the Quick Scan, **Add bus** and new channels follow them, and they are saved with the setup.

(si-scan)=
## Quick Scan

Choose **Every signal net** or **The nets ticked in Board**, and click **Scan**. The table lists each net (pairs together: nets named `_P`/`_N`, `+`/`-`, `DP`/`DM` and the like) with its result (failing first), its impedance range, length, worst crosstalk coefficient and the aggressor, any length without a reference, its longest via stub and its pair skew. Select a net for each finding and where it is. With **Quick Scan impedance in 3D** (in Settings), the 3D view colors the scanned traces by how far their impedance is from target: blue below, red above.

Targets: **Z0 target** for single-ended nets; for pairs, **Zdiff target**, or by name (USB 90 Ω, USB4 and PCIe 85 Ω, else 100 Ω): the net's own name first (PCIe's lane names, PETp0 or M2\_PER3\_N, count as PCIe), its sheet's only when that says nothing, so a lane on a sheet named for USB4 is not taken for USB4. **Make a channel** adds the selected net (and its pair) as a channel, with its worst neighbour as an aggressor.

**Slow nets**: nets named as slow controls are left out unless this is ticked. These are enables, resets, power-good, LEDs, interrupts, I²C, JTAG, FPGA configuration and straps, and their impedance seldom matters. The summary under the table names the nets left out. Pairs are always scanned, and so is every net when you scan **The nets ticked in Board**.

**Speed.** The scan is a first look, so each cut keeps only what affects its trace: the copper between the trace's nearest solid planes above and below, out to five times its height over them on either side (more for a pair, to cover its partner). Cuts that come out alike are solved once, with a mesh about 2 % coarser in accuracy than a channel's. The solves run in parallel on all but one of the CPU cores, and a second scan of the same board reuses the first one's cuts and solves. On ThunderScope (6 layers, 390 signal nets, about 28,000 cuts) the first scan takes about 3 minutes on a 6-core laptop, and a rescan a few seconds. Channels are solved at full accuracy.

(si-channels)=
## Channels

**Add bus…** makes many channels at once, for a memory interface, an ADC's data lanes or SerDes lanes. Pick the **Transmitter** part (parts with the most signal nets first) and the **Receiver** (the parts joined to it, with how many nets join them). Every signal net between the two is listed, also through series resistors and AC-coupling capacitors. Pairs are found by name, and nets are grouped and numbered by name (DQ0–DQ7, DQS0, A0–A15). Tick the nets, or use **Tick group** to pick one group, such as one byte lane's DQ. Then choose the **Interface** (or let each net's name choose it) and the **Neighbours as aggressors**: with 1, DQ3 gets DQ2 and DQ4 as its aggressors. Each channel gets both ends set. Nets that are already channels are greyed out. For a bidirectional bus, add it again with **Swap** to get the reads.

- **Net** and **Pair with**: a single-ended net, or a pair's positive and negative legs. **Through series parts** follows them through series resistors and capacitors (read from their values) to the nets beyond.
- **Not fitted**: more parts this channel leaves off, comma separated, on top of the build's (Settings, **Build**): for a board whose variants are kept outside KiCad, list them from the variant's BOM. The channel does not go through them; their empty pads stay on it as stubs. Under it, **Also not fitted** names the build's parts on the channel's nets.
- **Interface**: Custom, LVDS, USB 2.0 and 3.2, USB4 Gen 2 and 3, PCIe 2 to 5, SATA III, HDMI 2.0, SGMII, 10GBASE-KR, MIPI D-PHY, DDR4 DQ or CMOS logic. It sets the rate, swing, edge, terminations, equaliser and the limits checked. Any of them can be overridden below; at its lowest, a field shows *interface's* and uses the interface's value.
- **Transmitter** and **Receiver**: pick from the parts on the channel's nets (series parts left out), or type a reference. **guessed** shows the part KiPI-SI would use: the net's two farthest parts, an IC driving, or, with one end set, the part farthest from it. **Swap** turns a bidirectional net round (a DDR read instead of a write).
- **Aggressors**: nets whose near- and far-end crosstalk into the channel is solved with it, and added to its eye.
- **Driver buffer** and **Receiver buffer**: **Generic** (a supply, an output resistance, a 0–100 % edge and a pad capacitance; **Match generic buffers to the interface** fills them in, both ends' pad capacitance the interface's), or an **IBIS model**: the `.ibs` file, its model, the pin (for its own package R, L and C) and the corner.

(si-results)=
## Results

The channel's PASS, WARN or FAIL, and its checks:

```{list-table}
:header-rows: 1
:class: kipi-table

* - Check
  - Passes when
* - impedance
  - every section within the tolerance of the target (WARN: under 10 % of the length off)
* - insertion loss
  - at Nyquist, above the interface's limit
* - return loss
  - up to Nyquist, below the interface's limit
* - mode conversion
  - Scd21 below −25 dB up to Nyquist (pairs)
* - skew
  - P/N skew under 5 % of a UI
* - eye
  - the statistical eye at the BER covers the receiver's mask
* - COM
  - 3 dB or more (differential interfaces)
* - overshoot, ringback, monotonic
  - from the transient at the receiver's die: overshoot under 10 % of the swing, ringback clear of the thresholds, edges monotonic through them
* - crosstalk
  - each aggressor's NEXT and FEXT below −30 dB up to Nyquist
```

Below them: the notes (ports, nets, anything assumed), **Report** (HTML or PDF, with the channel's Touchstone file in it), **Report several…** (one report of the solved channels you tick: a summary of them all, then each channel; in HTML a picker at its top shows one channel or all), **Export Touchstone…** (`.s2p` or `.s4p`, 50 Ω, ports at the dies), **Export SPICE…**, **Save results…**, which keeps every solved channel and the Quick Scan, and **Open results…**, which brings a saved `.kipi_si-si-results` back for the board without solving again (also **File → Open results…** in SI mode).

**Export SPICE…** fits the channel's S-parameters with a rational model (vector fitting, common poles, as many as it takes for an RMS error under 0.2 %), makes it passive if it is not quite (no singular value over 1 from DC to twice the band), and writes it as a SPICE subcircuit, `.subckt kipi_si_<channel> p1 … pN ref`, with the port names in its comments. It uses only resistors, capacitors and controlled sources, so any SPICE (ngspice, LTspice, a vendor's) can run the channel with its own driver and receiver models.

(si-settings)=
## Settings

- **Build**: the parts left off. **As on the board** leaves off the parts marked DNP (do not populate) in KiCad; a KiCad 10 **assembly variant** leaves off its own DNP parts instead (a variant leaves a part as the board has it unless it says otherwise). No channel goes through a part left off, and Add bus does not join nets through one. A board read from the running KiCad gives its parts' DNP but not its variants: open the `.kicad_pcb` file for those.
- **Section length** and **Neighbour window**: how finely traces are cut, and how far either side copper is in their cross-section, at least. A trace high over its reference plane (a thick dielectric, a 2-layer board) is cut wider: 8 times that height past its edge.
- **Etch**: a trace's top narrower than its bottom by this, each side.
- **Copper roughness**: Smooth, Hammerstad or Groisse (from the RMS roughness), or Huray (nodule radius and surface ratio). Rough copper adds loss as the skin depth shrinks.
- **Model vias**: untick to join layers at vias with no via model.
- **Highest frequency** and **Step** of the sweep: by default up to five times Nyquist (and at least three over the edge), the step small enough for 64 UI of response.
- The Quick Scan's targets and limits.
- **3D view**: **Quick Scan impedance in 3D** colors the scanned traces by their impedance, **Solved channel's impedance in 3D** the shown result's line sections; **TX and RX labels in 3D** marks the selected channel's Transmitter and Receiver with their parts' names (*TX U1*, *RX J2*).

The dielectrics' loss tangents come from the board's stackup where it has them, else the AC setup's loss tangent.
