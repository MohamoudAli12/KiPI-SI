(ac-setup)=
# AC setup tabs

Switch **Mode** to **AC**. The setup dock becomes the **AC setup**; it edits the same setup file as DC.

(ac-vrms)=
## VRMs and Series links tabs

*Shared with DC*

The same VRMs and series links as the DC setup; edits in one mode show in the other. Every VRM field can be edited in either mode; the tooltip of a field only DC uses says so. In AC:

- A VRM's output net (and ground pins) define a rail and its default ground for the **Rail** picker.
- A series link adds its **ESL** to its resistance. A link leading off the rail to a net that is not part of the solve is left out, with a note. A 0 Ω link with no ESL merges the two nets.

(ac-caps)=
## Capacitors tab

*RLC models and which parts use them*

A **model** is a capacitance, ESL and ESR shared by a group of identical parts. All three are required.

```{list-table}
:header-rows: 1
:class: kipi-table

* - Control
  - What it does
* - **Models from values**
  - Creates one model per distinct value among the capacitors that have none yet, named after the value, with the capacitance read from it, and the voltage rating when the value gives one (`10uF 6.3V X5R`). Enter ESL and ESR yourself.
* - Capacitance
  - Per part, with no DC bias. For a ceramic, enter its **Voltage rating** to estimate DC bias, or enter the effective value at the rail's voltage if the datasheet gives it.
* - ESL
  - The part's own inductance (datasheet), not including mounting.
* - ESR
  - Per part.
* - **Import SPICE model…**
  - Uses the part's SPICE model from its maker (see below). Pick its subcircuit from the file; the dialog shows the values fitted to it before you accept. The subcircuit is saved in the setup, so the setup file carries it. With **Use the SPICE model's impedance** ticked, the AC and Coupled Noise solves take each part's impedance from the model at every frequency, which follows a ladder model's shape where a series RLC cannot. The capacitance, ESL and ESR are then fitted to it and locked, for the tables and reports: C and ESL from its reactance 30 times below and above its self-resonance, and ESR its resistance at resonance. DC bias, aging, temperature and tolerance scale every capacitor in the model alike. Untick to use the values as you type them; the model is kept, and ticking again puts its fitted values back.
* - Voltage rating
  - The part's rated DC voltage. Class II ceramics (X5R, X7R, X6S…) lose capacitance with DC voltage; with a rating, each part's capacitance is derated by the DC voltage across it: what the last DC solve found across its pads, or else the rail's VRM regulated voltage. The Results notes and the HTML report give the voltages and the capacitance left. **Models from values** fills it in for values naming a class II dielectric. Leave it **not set** for polymer and electrolytic parts; a model with a C0G dielectric is never derated.
* - Dielectric
  - The ceramic dielectric (C0G, X7R, X5R, Y5V…), for aging and temperature. Picking one fills in its typical aging rate, and with a **Temperature** in the Sweep tab the capacitance follows the dielectric's typical curve from its rated value at 25 °C (X7R: −4 % at 85 °C and −12 % at 125 °C; Y5V: −75 % at 85 °C; C0G: flat). Leave it unset for polymer and electrolytic parts, which are then not aged. **Models from values** reads it from the value (`NP0` counts as C0G).
* - Aging
  - Capacitance lost per decade of hours operated, in % (X7R about 2, X5R about 3, Y5V about 7; C0G does not age). Enter the datasheet's rate if it gives one. Used when **Aging** is ticked under Capacitor derating in the Sweep tab.
* - Manufacturing tolerance
  - Optional: the part's capacitance tolerance, in % of nominal, from its datasheet or its value code (J is ±5 %, K ±10 %, M ±20 %). Used when **Manufacturing tolerance** is ticked under Capacitor derating in the Sweep tab, which solves the model at the low end of it. Leave it **not set** for a part whose entered capacitance is already the figure you want simulated.
* - Kept at rating
  - How much of its capacitance the part keeps at its rated voltage, from the datasheet's DC bias curve (40 % by default; often 30 to 50 %, and less for smaller cases). Between 0 V and beyond the rating, the capacitance follows C / (1 + k (V / V{sub}`rated`){sup}`1.5`), a typical X5R/X7R curve's shape.
* - Filter box
  - Narrows the parts table by reference, value, footprint, net or model.
* - Parts table
  - Every capacitor (reference `C…`) whose pads are all on ticked nets, across two nets, with its footprint (hover for the library). Tick a part to give it this model; it moves from any other model. Grayed rows already belong to another model, named in the last column. Click a column header to sort by it.
* - **Tick same value / footprint / value + footprint**
  - Ticks every part matching the selected row: the same value, the same library footprint, or both (e.g. only the 0402 100 nF parts, whose ESL differs from the 0603 ones).
* - **Tick shown / Untick shown**
  - Applies to every row the filter shows.
```

```{figure} /images/ac_capacitors.png
:alt: The Capacitors tab with a model and its parts

A capacitor model and the parts that use it.
```

(ac-probes)=
## Probes tab

*Where the impedance is measured, and its target*

```{list-table}
:header-rows: 1
:class: kipi-table

* - Field
  - Meaning
* - Name
  - Shown in the plot legend and the table; follows the supply part by default.
* - Supply pins
  - The device's power pins. Picking a part also picks its ground pins if it has any.
* - Ground pins
  - On the ground net being simulated, or on another ground a series link ties to it: an analog ground joined to GND by a net tie, a 0 Ω resistor or a ferrite. Add that part as a series link between the two grounds; the solve then meshes both grounds as one return, with the link in it (a link with no resistance or ESL joins them outright).
* - Target
  - **Flat, up to a frequency**, or **Custom (piecewise linear)**.
* - Target |Z| / Target frequency
  - Flat target: PASS if |Z| stays at or below it from the VRM's control loop bandwidth up to the frequency (*none*: to the end of the sweep).
* - Calculator…
  - Opens the {ref}`Target Impedance/Frequency Calculator <ac-calc>`.
* - Custom points
  - Frequency/|Z| corner points, joined by straight lines on the log-log plot. Below the first point the first |Z| holds, above the last the last holds. **Add point** adds one a decade above the last; ✕ removes one.
* - Load step (ΔI) / Load step slew rate
  - Optional. How far and how fast the device's current steps. With both, and the VRM's control loop bandwidth, the solve estimates the rail's {ref}`transient response <ac-transient>` at this probe. The calculator fills them in, and so does a load model with a load step.
```

**From DC load** adds a probe on the same supply and ground pins as a DC load picked from its dropdown. The dropdown also lists the input of every LDO and switcher, one entry per phase (e.g. *VR4 phase 2 input*): a regulator's input pins load the rail feeding it just as a device does.

**Model ▾** applies a {ref}`load model <load-models>`'s targets to many probes at once, adds a model's probes for the parts ticked, or exports a part's model.

A rail can have several probes, e.g. one per device; they are all solved together and each sees the others as open circuits.

**From package model…** reads a device's {ref}`package model <ac-packages>` and adds probes on its die.

(ac-packages)=
## Packages tab

*Package PI models, for probes on the die*

Vendors give a device's package as an N-port Touchstone file (`.sNp`): ports on the package balls, where it meets the board, and ports on the die. **Add** (or **From package model…** in the Probes tab) reads one, Touchstone 1 or 2 with S, Y or Z data, and asks which board part it is the package of. The whole file is kept in the setup file. Port names found in the file's comments (`! Port[1] = VCCINT_BGA`) connect the ports: a port named for one of the part's nets goes to that net, on the die if its name says so (*die*, *bump*), else to the PCB. **Connect ports by their names** does that again.

In the ports table, each port connects to:

- **PCB pins**: the part's pins on its **Net** (the **Pins** listed, or every one) against its pins on the **Ground net**. The solve joins the package to the board there.
- **Die probe**: a probe in the Probes tab, named after the port, on the rail of its net. It has no place on the board: its impedance is looked into at the die, through the package. Its targets and load step are set like any probe's. Removing it leaves the port open.
- **Open** or **Shorted**: left unconnected, or shorted to its reference.

The package also loads the board's own probes, which see its die through the balls. PCB ports on another rail are left open when this rail is solved. Outside the file's frequency range the model is held at its first and last frequency, and the solve says so. The Coupled Noise mode shows a die probe's ripple at the part's pins, without the package.

(ac-bandwidth)=
## Targets and the VRM bandwidth

The AC solve leaves the VRM out of circuit: it gives the **open-loop** PDN impedance, which keeps rising toward low frequency. In the real circuit the converter's control loop holds the rail below its bandwidth. So the rail's VRM needs a **Control loop bandwidth** before the rail can be solved, and a probe's target (flat or custom) applies only from that frequency up:

- the plot draws the target only above the bandwidth, and marks the bandwidth with a dotted line;
- PASS/FAIL, the worst |Z| and the margin only look above it. Without a target, the worst |Z| is the highest above the bandwidth;
- the cursor shows "none here" below it.

**Fallback:** if the bandwidth is at or above a flat target's frequency, or above the whole sweep, no frequencies are left to judge. That probe's target is then judged over its whole range, and a note in the results says so.

(ac-calc)=
## Target Impedance/Frequency Calculator

Works out a flat target from the device's transient spec:

- **DC load**: the DC load whose tolerance and current the copy buttons use. A load on the probe's own supply and ground pins is used directly. Otherwise the dropdown offers the loads on the probe's part: supply pins on the same footprint, and ground pins too where the load has them. An LDO's or switcher's input pins count as a load too: its **Input range** is the tolerance, and its input current and the DC drop at its input pins come from the last DC solve.
- **AC voltage tolerance**: how far the supply may move during a load transient, e.g. the AC part of a ±3 % spec on a 0.9 V rail: 27 mV.
- **Copy tolerance from DC load** fills the AC voltage tolerance from a DC load's tolerance: ± its tighter side, from the voltage of the VRM feeding it (2 % for -2 % / +5 %). A DC tolerance is the whole budget, and the DC drop uses up part of it, so lower the value if the AC part is smaller.
- **Copy AC tolerance from DC load** fills it from the load's own **AC tolerance**, where it has one (it is greyed out otherwise): ± its tighter side. That is already the swing allowed about the DC voltage, so there is no DC drop or VRM accuracy to subtract from it.
- **Subtract DC drop at the load** takes the DC drop the copper causes at the selected load's own pins off the AC voltage tolerance, so what is left is the budget for the transient. It reads the last DC solve: its effective voltage there (supply pins minus ground pins) against the target voltage of the VRM driving it, so **solve the power tree on the DC tab first** — without a result for that load the button stays disabled and says so. A drop uses up room below the target; a load above it (a remote-sensed VRM raises pins near it) has its boost taken off the room above. Each click subtracts again.
- **Subtract VRM DC accuracy** takes the DC accuracy of the LDO or switcher driving the probe's rail off the AC voltage tolerance, as the output may already sit that far from its regulated voltage. After **Copy tolerance from DC load**, each side of the accuracy comes off the same side of the load's tolerance, and the AC tolerance is the smaller room left: a load allowed -5 % / +3 % of 1 V behind a VRM accurate to -3 % / +1 % has 20 mV left on both sides. A value typed in has no sides, so the larger side of the accuracy comes off it (30 mV here). It shows a menu when several VRMs drive the rail; each click subtracts again.
- **Load step (ΔI)**: the size of the current step.
- **Copy current from DC load** fills the load step from a DC load's current, a step from no load to all of it. Lower it if the device's current steps by less.
- **Load step slew rate**: how fast it steps, A/µs; 10 A/µs until you change it.

Then Z{sub}`target` = V{sub}`AC` / ΔI, flat up to f{sub}`target` = 1 / (π · t{sub}`rise`), with t{sub}`rise` = ΔI / slew rate. **Use for probe** fills the probe's target fields and its load step (for the {ref}`transient <ac-transient>`); the inputs are remembered for next time, and a probe that has a load step opens the calculator with it. The target applies above the VRM's control loop bandwidth ({ref}`Targets and the VRM bandwidth <ac-bandwidth>`).

The target impedance method was introduced by L. D. Smith, R. E. Anderson, D. W. Forehand, T. J. Pelc and T. Roy, "[Power Distribution System Design Methodology and Capacitor Selection for Modern CMOS Technology](https://doi.org/10.1109/6040.784476)," *IEEE Transactions on Advanced Packaging*, vol. 22, no. 3, pp. 284–291, Aug. 1999.

```{figure} /images/ac_target_calc.png
:alt: Target impedance calculator dialog

The calculator: 27 mV over a 10 A step at 10 A/µs gives 2.7 mΩ up to about 318 kHz.
```

(ac-sweep)=
## Sweep tab

```{list-table}
:header-rows: 1
:class: kipi-table

* - Field
  - Meaning
* - Start / Stop
  - Frequency range.
* - Points per decade
  - Resolution of the plotted curve. Cheap: the parts are evaluated at every point.
* - Field solves per decade
  - How often the copper itself is solved; in between, its response is interpolated (smoothly, it varies slowly). Where it does not vary slowly (around the planes' cavity resonances) the copper is solved at the sweep's own points as well, so those solves come on top; the log says how many. *Every point* solves the copper at each sweep frequency: exact and slowest. If the Notes say a resonance changes faster than the sweep's points resolve, raise **Points per decade**.
* - Capacitor derating
  - DC bias, manufacturing tolerance, temperature and aging, grouped together. The results and the report list each one and whether it was applied (and why not: unticked, or no model on the rail has what it needs); the report's capacitor model table gives each model's derated capacitance and the self-resonance it moves to.
* - DC bias
  - Ticked (the default), the capacitor models with a **Voltage rating** are derated by the DC voltage across each part. Untick it to solve with every model's capacitance as entered.
* - Manufacturing tolerance
  - Ticked, every capacitor model with a **Manufacturing tolerance** is solved at the low end of it: the tolerance is subtracted, so a ±10 % model keeps 90 % of its capacitance and a ±20 % model 80 %. That is the worst case for a PDN, where too little capacitance raises the impedance. Models without a tolerance are unchanged. This multiplies with the DC bias estimate, aging and temperature. Off by default.
* - Temperature
  - *Not modeled* (the default): copper at 20 °C and capacitors at their rated values. *Fixed*: the whole board at **Board temperature**. *From DC thermal co-simulation*: each copper triangle and capacitor at the temperature the last DC solve with thermal co-simulation found there, on its own copper layer; DC results opened from a file work too. Without one, the AC solve uses the Board temperature and says so. The copper's resistivity follows its temperature coefficient (from the DC settings), and models with a dielectric follow its temperature curve.
* - Board temperature
  - The temperature when Fixed, and where the thermal co-simulation gives none.
* - Aging
  - Ticked, every capacitor model with a dielectric loses its aging rate for each decade of **Hours operated** past 1000 hours (the usual reference age of the rated capacitance): an X7R part at 2 %/decade keeps 96 % after 100,000 hours. This multiplies with the DC bias estimate. Off by default.
* - Hours operated
  - How long the capacitors have aged, in hours (8760 a year; 87,600, ten years, by default). Heating a ceramic past its Curie point, as in reflow soldering, restarts its aging. While aging is ticked, a slider under it sets the hours from 1000 to 1,000,000 on a log scale, with the time in years beside it.
```

(ac-mesh)=
## Mesh tab

```{list-table}
:header-rows: 1
:class: kipi-table

* - Field
  - Meaning
* - Max edge
  - Largest element, mm.
* - Via grading
  - Element growth per mm away from plated holes.
* - Min edge (at holes)
  - Element size at plated holes. The mesh here decides the via and mounting inductance.
* - Grade only near the rail
  - On by default. The mesh is refined only at plated holes within five board thicknesses (at least 5 mm) of the rail's copper or a part on it. Far ground vias carry almost none of the rail's current, but grading them can be most of the mesh on a board stitched with many. All the copper is kept either way, so the low-frequency return still takes every path it has. On an 8-layer board it halved the solve and changed the impedance by under 0.002 %.
```

The via plating rules come from the DC setup's Mesh tab; copper resistivity and the dielectric **Loss tangent** and **Default εr** from the {ref}`Stackup window <stackup>`.
