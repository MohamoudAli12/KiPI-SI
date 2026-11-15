(dc-setup)=
# DC setup tabs

The **PI setup** dock on the right. **Save** at its top writes the setup next to the board (DC and AC share one file). **Import…** beside it fills the VRMs, loads and series links from a Tomachie power-tree file (`<schematic>.pdn.json`, see {ref}`Files <files>`), keeping the settings, thermal and AC setup. The typical current and resistance are solved; each maximum the file gives is kept for a **Worst case (max)** solve, chosen beside **Solve all**. A current the file does not give is marked not known, and the results it touches are INCOMPLETE. The log lists what could not be placed on the board. Problems that stop a solve are listed in red under the tabs as you edit. The VRMs, Loads and Series links tabs share one layout: a list with **Add**, **Duplicate** and **Remove**, and an editor for the selected entry below it.

(dc-vrms)=
## VRMs tab

*Regulators and supplies*

```{list-table}
:header-rows: 1
:class: kipi-table

* - Field
  - Meaning
* - Name
  - Used in the results tables.
* - Type
  - **Source**: an ideal supply with no input (connector, bench supply, battery). **LDO**: I{sub}`in` = I{sub}`out` + I{sub}`q`. **Switcher**: P{sub}`in` = P{sub}`out` / efficiency. **Isolated**: a switcher whose output side has its own ground (see {ref}`isolated converters <vrm-isolated>`).
* - Target voltage
  - The rail's target: the VRM regulates to it at its output (or sense) pins, and loads are judged against it. Read from the net name when you pick the output net (see {ref}`pre-filled fields <autofill>`).
* - Efficiency
  - Switcher and isolated only.
* - Quiescent
  - LDO, switcher and isolated: extra input current.
* - Output current limit
  - Optional. The VRM row shows PASS if its total output current (all phases) is at most this.
* - Load line
  - Optional, DC only (adaptive voltage positioning). The VRM regulates to its regulated voltage less this resistance times its output current: what its connected loads and the VRMs it feeds actually draw, so a {ref}`disconnected <ts-no-path>` load adds no droop. Drops are still measured from the regulated voltage, so the droop counts against each load's tolerance. The Notes tab, the HTML report and the VRM CSV show the droop and the voltage it regulates to (**V target**). **none** holds the regulated voltage.
* - Dropout
  - LDO only: the least input-to-output difference at which it still regulates.
* - Input range
  - Optional input range, min and max on one row, in **V**, in **±V** from the input rail's nominal voltage (the target voltage of the VRM driving it; e.g. min -0.5 V, max +0.5 V) or in **%** from it (e.g. min -10 %, max +10 %). Switching the unit converts the values when that VRM is known. A range in ±V or % with no VRM driving the input is a setup error. A VRM whose solved input is outside its range (or an LDO below its dropout) cannot hold its output, and every load it feeds, directly or downstream, is marked {bdg-danger}`VRM OUT OF REGULATION`.
* - DC accuracy
  - LDO, switcher and isolated only; used by the AC {ref}`target calculator <ac-calc>`. The output's DC error (DC accuracy or DC tolerance) from the datasheet: the regulator's reference accuracy, the feedback resistor tolerances, leakage into the FB pin, and line and load regulation. Min and max on one row, in **%** of the regulated voltage (e.g. -1 %, +1 %), in **±V** from it (e.g. -0.01 V, +0.01 V) or in **V**, the lowest and highest output voltage.
* - Control loop bandwidth
  - AC only. Also called the loop gain crossover, gain crossover or control loop crossover frequency; it depends on the total output capacitance and the loop tuning. The AC solve leaves the VRM out of circuit, so it gives the *open-loop* PDN impedance; below this frequency the converter's loop holds the rail. Probe targets are drawn and judged only above it (see {ref}`Targets and the VRM bandwidth <ac-bandwidth>`). Required in AC mode: a rail whose VRM has none cannot be solved.
* - Phases / Edit phase
  - Multi-phase regulators. See {ref}`the multi-phase workflow <wf-multiphase>`.
* - Output pins
  - Where it drives the rail: the output pin, or for a switcher usually the inductor's output side.
* - Input pins
  - LDO, switcher and isolated: where it draws its input. This links it into the power tree. Filled in from the output part when it has one other rail.
* - Ground pins
  - Optional: solve the ground return as well. Filled in with the output part's ground pins. On an isolated converter, **Output ground pins**: the output side's ground, which they hold at 0 V.
* - Input ground pins
  - Isolated only, optional: the input side's ground pins, where its input current returns to the VRM feeding it. Filled in with the output part's pins on its other ground net.
* - Sense pins
  - Optional remote sense (positive).
* - Ground sense pins
  - Optional negative remote sense on the ground net (needs ground pins).
* - Mesh sense
  - Off by default. Any number of sense points (**Sense points**, edited one at a time with **Edit sense point**), each with its own sense and optional ground sense pins. Every point's sense pins are held at the regulated voltage (less the load line), above its own ground sense pins; the VRM's current enters there and its output pins only measure.
```

(dc-loads)=
## Loads tab

*Parts that draw current*

```{list-table}
:header-rows: 1
:class: kipi-table

* - Field
  - Meaning
* - Name
  - Defaults to the supply part's reference.
* - Supply pins
  - Where the current is drawn.
* - Current split
  - **Equal across the supply pins**, or **Per pin group**: a table of groups, each with its own pins and current. **Add pin group** adds a row; **One group per pin** replaces the table with one row per supply pin, sharing the total. ✕ removes a row. Use groups when a part draws different currents on different pins.
* - Current
  - The load's total current (equal split). Negative values are allowed for parts that source current.
* - Ground pins
  - Optional: include the load's ground return. Filled in with the supply part's ground pins.
* - Tolerance
  - Optional min and max on one row, in **%** from the VRM target voltage (e.g. min -3 %, max +5 %), in **±V** from it (e.g. min -0.1 V, max +0.15 V) or in **V** (e.g. 3.135 to 3.465 V). Either may be left "not set". PASS if every supply pin is within it. Switching the unit converts the values when a VRM drives the load's rail.
* - DC tolerance, AC tolerance
  - Optional, for a part that gives its tolerance in two shares as well as in total: the DC share, where the pin's steady voltage may sit (the VRM's accuracy and the copper's DC drop together), in the same units as the tolerance; and the AC share, how far ripple and load transients may swing it from there, in **±V** or **%**. They are saved with the setup for a later analysis, and the AC target calculator can copy the AC one; no solve reads them, and PASS still follows the tolerance above.
```

```{figure} /images/setup_loads.png
:alt: The load editor

The load editor.
```

**Split across nets…** under the list shares one part's total current over several of its supply nets, as a load on each: for when only the part's total draw is known and some of its pins are on a net of their own, behind a ferrite bead say. Pick the part, give its total current and tick the nets (its grounds are left out). **Equal per pin** gives each net its pins' share of the total; **Equal per net** the same to each. A net the part already has a load on gets that load's current set (its pin groups are cleared); the others get a new load, with the part's ground pins.

(load-models)=
### Load models

A **load model** is a part's supplies in a YAML file of their own: for each supply its pins, current or pin groups, tolerance and heat, and for the AC analysis its target impedance, or the load step it is worked out from. One model serves every copy of a part, on this board or another. The **Model ▾** button under the Loads list (and under the AC Probes list) has:

- **Apply model file to loads…**: pick a model, then tick the loads to apply it to, each with the model supply to take beside it. Loads whose pins or name match a supply come ticked. Only what the model gives is set; pins are left as they are.
- **Add loads from model file…**: one load per supply on each part ticked. The list holds the parts that have the pins of at least one of the model's supplies; a load's net is the one its pins are on, and its ground pins are the model's or, without them, guessed as for a new load.
- **Export a part's model…**: every load and probe on one reference designator, one supply each (named after the load, less its reference), so a part with several supplies keeps them all.

On the Probes list the same menu sets targets: the model's flat target or custom points, or one from its load step and slew rate, as the target calculator works it out, with the tighter side of the supply's AC tolerance (without one, of its total tolerance of the rail's VRM voltage). A model file, by hand:

```yaml
kipi_si_load_model: 1
part: XC7A35T-1CSG324C
supplies:
  - name: VCCINT
    pins: [F7, F9, H7]
    ground_pins: [A1, A10]
    current_a: 1.2              # or pin_groups: [{name: core, pins: [F7], current_a: 0.8}, ...]
    tolerance: {min: -3, max: 3, unit: "%"}     # total: V, ±V or %
    dc_tolerance: {min: -1.5, max: 1.5, unit: "%"}     # VRM accuracy + DC drop: V, ±V or %
    ac_tolerance: {min: -0.03, max: 0.03, unit: "±V"}  # ripple + transient: ±V or %
    target: {ohm: 0.01, up_to_hz: 50.0e6}      # or {points: [[1.0e3, 0.01], [1.0e8, 0.1]]}
    load_step: {step_a: 0.6, slew_a_per_us: 5}
```

Every key but `name` is optional. `dc_tolerance` and `ac_tolerance` are a load's **DC tolerance** and **AC tolerance**. Models from before 0.9.2 gave the AC tolerance as `ac_tolerance_mv` in `load_step`; that is still read, as that many mV either way.

(dc-links)=
## Series links tab

*Parts between two nets*

Sense resistors, ferrite beads, fuses, load switches, 0 Ω links: any part that passes DC from one net to another. Give the part's **Side A pins** and **Side B pins** and its **Resistance (DCR)**; 0 is a short. Picking side A on a two-terminal part fills in side B on its other net, and when both sides are on the same resistor, the resistance is read from its value field (`10m`, `4k7`, `0R1`, `5 mΩ`…). **ESL** is used by AC only. A new link starts on a part that bridges the first two ticked nets that are not grounds, if there is one.

**Estimate ESL** fills in the ESL for you:

- **From package** uses the size of the part on side A. It reads the size from the footprint's name (`R_0603_1608Metric`, `RESC2012X65N`, `0805`), or else from how far apart the part's two pads are. The estimate is 0.1 nH + 0.3 nH for each mm between the terminals. That line runs through Vishay's measured 0402 and 0603 chip resistors (0.4 and 0.6 nH), and gives 0.7 nH for an 0805, 1.1 nH for a 1206 and 2 nH for a 2512. It suits a chip resistor, fuse or jumper. A ferrite bead's ferrite makes its inductance far larger, so use its impedance instead.
- **Ferrite bead…** asks for the bead's impedance |Z| at one frequency, read off its datasheet's curve, and works out L = √(|Z|² − DCR²) / 2πf. Choose a point well below the curve's peak, where |Z| still climbs in a straight line. At and above the peak the bead acts as a resistor, so a point there (such as the 100 MHz headline figure of many beads) overstates the inductance.

**Import SPICE model…** uses the part's SPICE model from its maker, a ferrite bead's say. Pick its subcircuit from the file; the dialog shows the values fitted to it before you accept. The subcircuit is saved in the setup. With **Use the SPICE model's impedance** ticked, the AC and Coupled Noise solves take the link's impedance from the model at every frequency, so a bead keeps its resistive peak. The DCR and ESL are then fitted to it and locked: the DCR is its resistance at DC (which the DC solve uses), and the ESL its inductance at 100 kHz, low on a bead's inductive slope. Untick to use the values as you type them; the model is kept.

**A diode** is imported the same way: pick its `.model … D(…)` card, or a two-pin subcircuit with diodes in it, and make side A its anode (the model's first pin). The dialog shows its forward voltage at 1 mA, 100 mA and 1 A. The DC solve takes the drop from the model at the current the diode carries, so the drop rises with the load. The AC and Coupled Noise solves use its small-signal resistance (n·V{sub}`T`/I + RS) and its junction and diffusion capacitance at the current the last DC solve found through it, or, without a DC solve, at an estimate: what the loads and VRM inputs on side B's nets draw at nominal voltages (nothing, so the diode blocks, when a VRM drives side B). The solve's notes say which. The DCR and ESL shown are its slope resistance and inductance at 1 A. A diode that is reverse biased with a load beyond it and no other supply has no DC solution, and says so. The junction is read at 27 °C. Setups from 0.9.2 with a constant forward drop load with a diode model of that drop.

**What KiPI-SI reads from a SPICE file.** A two-pin `.SUBCKT` of resistors, inductors, capacitors and diodes, which is how makers model capacitors, resistors, ferrite beads and diodes, or a diode's `.model D` card. Diodes use IS, N, RS, BV, IBV, CJO, VJ, M, FC, TT and an area factor; LTspice's piecewise-linear diode (Ron, Vfwd) is not read. It may call other subcircuits in the same file, use `.param` values and arithmetic, and use LTspice's `Rser`, `Lser`, `Rpar` and `Cpar`. 0 V sources (current probes) are read as shorts. Anything else (transistors, controlled or behavioral sources, coupled inductors) is refused with the element named, and `.include` lines are not followed. The file is only read, never run. Models of switching regulators and other active parts are not for this; give a VRM or load its own values instead.

The nets a link joins are solved together as one group, so a group can only hold one VRM. A load pin with no copper path to its VRM is reported, not guessed at (see {ref}`Loads not connected by copper <ts-no-path>`).

(dc-solve-tab)=
## Solve tab

*Choose which net groups to solve*

Lists every net group with its role (rail from a VRM, ground, or not driven). Untick groups that are not modeled or routed yet; **All** and **None** tick or untick them all. Only ticked groups are validated and solved, and the choice is saved. Each VRM in the **VRMs** tab has a tick box too: it ticks or unticks that VRM's rail here, so to solve one VRM alone, untick the others. Where a solved group meets an excluded one:

- A VRM whose *output* is excluded becomes a constant load on its input pins, drawing the input current its rail would need at nominal voltages.
- A VRM whose *input* is excluded is treated as an ideal source.
- Ground pins on an excluded ground are ignored.

The Notes results tab lists what was left out and substituted. The Solve button shows how many groups will be solved, e.g. **Solve 3 of 5 net groups**.

```{figure} /images/dc_solve_tab.png
:alt: The Solve tab listing net groups with checkboxes

The Solve tab of the example board.
```

(dc-mesh)=
## Mesh tab

```{list-table}
:header-rows: 1
:class: kipi-table

* - Field
  - Meaning
* - Max edge
  - Largest triangle edge, mm. Smaller is more accurate and slower. Raise it for quick looks at big boards.
* - Via grading
  - How fast elements grow away from plated holes, where current crowds. Lower keeps the mesh fine further out; 0 turns grading off.
* - Via plating
  - A table of rules, first match wins: hole type, drill range, plating (µm, growing inward from the drill) and what a filled hole is filled with. A via the KiCad board marks as filled carries its core too when the fill conducts. Defaults: IPC-6012 Class 2 minimum averages.
```

The defaults suit most boards; set the via plating your fabricator states.

```{figure} /images/setup_mesh.png
:alt: The Mesh tab with the via plating rules

The Mesh tab and its via plating rules.
```

(dc-thermal)=
## Thermal tab

*Electro-thermal co-simulation, off by default*

Tick **Electro-thermal co-simulation** to let copper losses heat the board, with warmer copper becoming more resistive. KiPI-SI alternates electrical and thermal solves.

```{list-table}
:header-rows: 1
:class: kipi-table

* - Field
  - Meaning
* - Ambient
  - Air temperature around the board.
* - Iterations
  - Electrical/thermal passes. Three is usually enough; the Thermal results tab shows how much each changed.
* - Airflow
  - Air speed over both faces, m/s; 0 is still air. The air always flows parallel to the board, along both faces, and its direction is fixed: every point is cooled equally, as if the air stayed at ambient across the whole board, so upstream parts do not warm the air that reaches downstream ones. Convection is h = 10 + 3.8·v W/m²K per face. The heat crosses each face's solder mask and silkscreen on the way (Stackup window).
* - Grid
  - Thermal cell size; *auto* is about 250 cells across the board.
* - Include load power dissipation
  - Off by default. When ticked, each load heats the board with the power it draws: the sum over its supply and ground pins of pin current × pin voltage, spread over those pins. A load without ground pins is taken as returning at 0 V.
* - Max copper temperature
  - Optional limit: copper hotter than this on any layer is FAIL.
* - Max rise above ambient
  - Optional limit on the temperature rise.
```

Heat comes from every solved net and layer, vias, DC connections (I²R, at their pins), VRM conversion loss and, with **Include load power dissipation**, the loads. Each copper layer has its own temperature: heat goes onto the layer it is made on (a part's on the layers of its pads), crosses the laminate to the layers above and below, and goes down plated holes on any net. Only the top and bottom layers lose heat to the air. The report's **Component power dissipation** table lists the DC connections' and loads' heat. The limits grade the last solve straight away when you change them.

```{figure} /images/setup_thermal.png
:alt: Thermal settings

Thermal settings.
```
