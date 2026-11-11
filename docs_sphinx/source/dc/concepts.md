(dc-concepts)=
# DC concepts

## Net groups, the power tree and voltage references

### Net groups

KiPI-SI solves copper one **net group** at a time. A group is a net plus every net joined to it by a {ref}`series link <dc-links>`. For example, `+3V3` and `+3V3_FILT` joined by a ferrite bead are one group. Each group may be driven by at most one VRM. Ground nets used by VRM or load ground pins are their own groups.

### The power tree

A VRM's **input pins** make it a load on its upstream net. KiPI-SI solves the tree from the leaves back to the source: downstream rails first, then each VRM's input current (from its output current, efficiency or quiescent current) is applied as a load upstream. So the 12 V input rail carries the current of everything it feeds.

```{figure} /images/power_tree.png
:alt: Power tree block diagram of the multiphase buck example

The **Power tree** window: the multiphase buck example.
```

### Voltage reference

Voltages are measured against the source's ground (0 V). If ground pins are given, the ground return is solved too and a load's ground rises above 0 V. The figure to compare with the VRM's regulated voltage is the load's **effective voltage**: supply minus ground at the load.

(vrm-isolated)=
### Isolated converters

A VRM of type **Isolated** (a flyback, a forward converter or an isolated module) is a switcher whose output side has a ground of its own. Its **Output ground pins** hold that ground at 0 V: they are its reference, as a source's ground pins are on the input side, and the loads on its rails return their current to them. Its input current returns through its **Input ground pins**, on the ground of the side feeding it. The two grounds must not be joined by a DC connection; a converter whose grounds are tied is a switcher. An isolated converter has one phase. In AC mode its rails are solved against its output ground, and Coupled Noise does not model isolated converters as aggressors.

### Drop and boost

A **drop** is a pin below the VRM's regulated voltage. A **boost** is a pin above it, which happens with remote sense: the VRM raises its output to hold a sense point further down the copper, so pins nearer the VRM sit above the regulated voltage. A load is judged by its worst pin, whichever direction.

(pin-picker)=
## The pin picker

*Used everywhere pins are chosen*

Every "pins" field is three boxes:

1. **Net**: one of the nets ticked in the Board panel. Type to search.
2. **Part**: the parts with pads on that net, busiest first, shown as reference, value and pad count, e.g. `U4 TPS62130 (3)`. Type to search (`u4` is enough).
3. **Pins**: optional pin numbers, comma-separated, e.g. `1,2,5`. Blank means every pin of that part on that net; the placeholder lists them.

Optional pickers have `(none)` as their first net.

(autofill)=
## Pre-filled fields

*Guesses from the board, always yours to change*

As you pick pins, KiPI-SI fills in the fields that usually follow from them. Each guess only fills a field you have not set yourself (an empty field, or one it filled in for the previous part), and when the board does not give an answer the field is left as it was. Change anything it fills in: your value is kept.

```{list-table}
:header-rows: 1
:class: kipi-table

* - When you…
  - KiPI-SI fills in
* - pick a VRM's output net
  - **Target voltage** from the net's name: `+3V3`, `3.3V`, `V1P8`, `VDD_0V75`, `+12V`, `-5V`, `VBUS` (5 V). A name with no voltage in it (`VCORE`, `VIN`) leaves the voltage alone.
* - pick a VRM's output pins
  - **Ground pins**: the same part's pins on its ground net. For an LDO or switcher, **Input pins**: the same part's pins on its other rail, if it has exactly one. The VRM's **Name** follows the part while it is still the part's reference.
* - add phases to a VRM
  - Each new phase repeats the last one on the parts the next phase likely uses, with the same pin numbers:

    - the same parts on the next schematic sheet, when the board is annotated by sheet (`L101, Q101, Q102 → L201, Q201, Q202`, or `×1000`). Every one of the phase's parts must be there;
    - otherwise, the same step on as between the last two phases (`Q2, Q4 → Q6`), or the next parts in sequence (`L1 → L2`, `Q1 → Q2`).

    Without a next part, the phase copies the last one for you to edit.
* - pick a load's supply pins
  - **Ground pins**: the same part's pins on its ground net.
* - pick a series link's side A
  - **Side B**: when the part has pads on just two nets (a resistor, ferrite, fuse, inductor), its pins on the other net. Not for capacitors, or when the other net is a ground. When both sides are on one resistor, **Resistance** is read from its value.
* - pick a probe's supply pins (AC)
  - **Ground pins**: the same part's pins on the probe's ground net, or on its own ground net.
* - **Add** a VRM, load or series link
  - The same guesses for its first part. A new series link starts on a two-terminal part between the first two ticked nets that are not grounds.
```

**How the ground net is found.** Ground nets are not always called GND, so KiPI-SI tries, in order: ground nets the setup already uses (any VRM, load or probe ground pins), nets named like a ground (`GND`, `PGND`, `AGND`, `VSS`, `EARTH`…), then the board's biggest net (the one with the most pads) if it is not named like a rail. Only nets ticked in the Board panel are used, except grounds the setup already uses. Once one VRM or load has ground pins on an unusually named ground, every later guess uses it.

(tree-autofill)=
## Auto-fill power tree

*Every regulator and source at once; PI\_VRM, PI\_V, PI\_FSW*

**Auto-fill power tree…** on the setup bar finds every regulator on the board, the source each of their input rails comes in from, and the transistors that switch one rail on to another, and shows them in a preview to check before anything changes. **OK** fills each one's rail as {ref}`Auto-fill rail <rail-autofill>` does: its loads, series links and capacitor models.

How each part is recognised, the first that applies:

- its `PI_VRM` field (`switcher`, `ldo` or `source`), or the library's `vrm: {kind: smps}`;
- a **Switcher**: an inductor between a switch node and a rail. The switch node has an IC (or a FET) on it and no capacitor to ground; the rail has one. The IC is the switching device. Its output is the rail its feedback divider comes from (a net named like `FB` first): an inductor on the input with the divider on the far rail is a boost; otherwise a buck, with the inductor's pins on the rail as its output pins and the device's pins on its input rail as its input. Several inductors to one output are its phases;
- an **LDO**: an IC on exactly two rails (nets with a capacitor to ground and something else on them) with at most one signal to another part. A part with more, a level translator or a buffer on two supplies, is a load on both rails, not a regulator. The output is the lower rail by the names' voltages, else the one the IC is the only active part on. Two rails at the same voltage are a load switch, and left as a load;
- a **Switch**: a transistor joining a regulator's input rail, which nothing else feeds, to a rail that is fed (a P-FET load switch). It becomes a series link through the transistor, with the `PI_R` field as its on-resistance (else a short, in the notes);
- a **Source** on each regulator input rail still not fed: on its connector, else the transistor or diode the power comes in through (not a TVS to ground), else another part on it.

The preview lists them sources first, then down the tree. Untick a row to leave it out, change a **Type**, or, for a source, pick another **Part** from the list. Orange cells are guesses to check. The **Voltage** comes from the part's `PI_V` field, the library, or the rail's name; a rail like `VCC` gives none, so its cell is red and **OK** waits for a value. A switch has no voltage of its own.

The rails filled replace their VRMs, loads and links (KiPI-SI asks first), so a wrong source from an earlier Auto-fill rail goes. A part that is a VRM's input is not a load on the rail feeding it: the VRM draws its input current from its own load. Parts not fitted (KiCad's DNP) are left out, so a 0 Ω strap option does not join two rails. Ground pins are set only with **Include the ground pins**, as in Auto-fill rail.

For {ref}`Coupled Noise <noise-aggressors>`: **Add** on the Aggressors tab lists the switchers found and fills their phases from the board: inductor, switch node, the device's input and ground pins (its own ground pins when the VRM has none) and the capacitors. The `PI_FSW` field (`600kHz`) or the library's `fsw_hz` gives the switching frequency; the edges and the datasheet values are still yours to enter.

(rail-autofill)=
## Auto-fill rail and part fields

*PI\_I, PI\_R, PI\_IMAX, PI\_PMAX, PI\_TOL, PI\_ROLE, PI\_ESL, PI\_ESR and pi\_parts.yml*

**Auto-fill rail…** on the setup bar fills one rail's power tree from the board. Pick the **Rail** and the part it is **Driven by** (the regulator or connector; the likeliest come first: a regulator {ref}`Auto-fill power tree <tree-autofill>` finds driving the rail, even a switcher not on it itself, then other regulators and connectors; a level translator and a regulator fed from the rail come last). KiPI-SI walks out from the rail's net and looks at every part with pads on it:

- the source part becomes a **Source** VRM on its pads on the rail, or, when it is a regulator Auto-fill power tree recognises, a **Switcher** or **LDO** with its input pins (a switcher's output pins on its inductor);
- a part that is another VRM's input is skipped: that VRM draws its current;
- a two-pad part to another net that is not a ground and passes DC (a ferrite, an inductor, a resistor up to **Follow resistors up to**, 1 Ω by default, or a part its fields or the library call a link) becomes a series link, and the walk goes on into the net beyond it;
- a capacitor from the net to a ground gets an **AC capacitor model**, one per value and package (`100nF 0402`), unless a model has it already ({ref}`below <autofill-caps>`);
- test points, bigger resistors (pull-ups, dividers) and parts not fitted (KiCad's DNP, unless a `PI_ROLE` says otherwise) are skipped;
- anything else becomes a load on its pads on the net.

The rail's existing VRMs, loads and links are replaced (KiPI-SI asks first); other rails and every setting stay as they are. Capacitor models are only added: a capacitor already in a model keeps it. The result is not saved until you press **Save**. Probes are not added: place them on the AC Probes tab, where the load matters.

**Removing** a VRM on the VRMs tab offers to remove the loads, series links and capacitor models on its rail too (its output net and the nets beyond its series links): what Auto-fill rail added with it. **No** removes the VRM alone. A model shared with another rail keeps its parts there.

(pi-fields)=
### Where the numbers come from

For each value, the first of these that gives it wins:

1. the part's **PI\_ fields**, set on the symbol in the schematic and copied to the board with **Update PCB from Schematic**;
2. the **parts library**, `pi_parts.yml`, by the part's manufacturer part number (below);
3. for a resistor (reference `R…`) only, its resistance from its **Value** field, or, when that is not a number, a **Val** or **Value** field.

Nothing is guessed. A load with no current is added at 0 A and a series part with no resistance as a short (0 Ω), and each is named in the log's notes, to fill in.

```{list-table}
:header-rows: 1
:class: kipi-table

* - Field
  - Sets
  - Examples
* - `PI_I`
  - A load's current: one total, or a current per group of pins
  - `230mA`, `1.2A`, `0.23`, `3,4=230mA; 12=0.4mA`
* - `PI_R`
  - A series part's DC resistance
  - `55m`, `0.1`, `55mΩ`, `0.1 ohm`, `0R1`
* - `PI_IMAX`
  - A series part's current rating, or the source's current limit
  - `2A`, `500mA`
* - `PI_PMAX`
  - A series part's power rating
  - `63mW`, `0.25W`
* - `PI_TOL`
  - A load's supply tolerance
  - `±5%`, `+/-5%`, `-3/+5%`, `±0.1V`, `±100mV`
* - `PI_ROLE`
  - What the part is, when KiPI-SI would take it for something else
  - `load`, `link`, `vrm`, `ignore`
* - `PI_ESL`
  - A capacitor's ESL, from its datasheet
  - `0.4nH`, `400pH`
* - `PI_ESR`
  - A capacitor's ESR, from its datasheet
  - `30m`, `5mΩ`
* - `PI_VRM`
  - A regulator's type, for {ref}`Auto-fill power tree <tree-autofill>`, when KiPI-SI can't tell from the board
  - `switcher`, `ldo`, `source`
* - `PI_V`
  - A source's or regulator's output voltage
  - `12V`, `3.3`
* - `PI_FSW`
  - A switcher's switching frequency, for Coupled Noise
  - `600kHz`, `1.2MHz`
```

Field names are upper case, exactly as above. The value's spaces at either end are ignored.

**Numbers.** A number, an optional SI prefix and an optional unit: `230mA`, `230 mA`, `2.3e-1A`, `500uA`, `500µA`. The prefixes are `p n u µ m k M`. The unit's case does not matter (`230ma` reads), and a bare number is in the base unit: amps, ohms or watts. Words (`1.2 amps`) are not read.

**PI\_I by pins.** When `PI_I` has an `=` in it, it is a list of pin groups, each `pins=current`:

- groups are separated by `;` or `|`;
- a group's pins by commas or spaces: `F7,F9=0.8A` or `F7 F9=0.8A`;
- a total and groups cannot be mixed: once there is an `=`, every part of the field must be a group;
- pins that are not on the rail are dropped, and a group left with no pins with them;
- groups set in a field have no names; to name them, use a {ref}`load model <load-models>` or the library.

A `PI_I` that cannot be read is named in the notes (`U5: PI_I '…' can't be read`), and the load gets its current from the library, else 0 A.

**When PI\_R is needed.** A resistor's value is read from its **Value** field, so a resistor needs no `PI_R`. The field is for series parts whose value is not their DC resistance:

- **ferrite beads** (`FB…`, `FL…`): the value is a part number or an impedance such as `120R@100MHz`, which is the impedance at 100 MHz, not the DC resistance (often tens of mΩ). This is why only `R…` parts have their resistance read from the value;
- **inductors** (`L…`): the value is the inductance, and the DCR is in the datasheet;
- **fuses, load switches, connectors** and any part given `PI_ROLE=link`;
- **a resistor whose value you want to override**: a 0 Ω jumper's value makes it a perfect short, and `PI_R=30m` gives its real resistance.

Without `PI_R` or a library entry, such a part is added as a short, with the note *no DC resistance (PI\_R or the library), taken as a short*.

**PI\_ROLE** changes how the walk treats the part: `load` makes it a load (even a resistor or capacitor); `link` a series part followed to its other net; `vrm` a regulator fed by the rail, added as a load (its input current); `ignore` leaves it out. Test points (`TP…`) are left out unless they have a role. Any other value is named in the notes and not used.

**PI\_IMAX and PI\_PMAX** are checked after each solve: the log lists every series part with a rating as *Series part ratings*, its current against `PI_IMAX` and its loss against `PI_PMAX`, each PASS or FAIL. On the source part, `PI_IMAX` is its current limit.

(autofill-caps)=
### Capacitors

The rail's capacitors to ground are grouped into one AC model per value and package. Each model's numbers come from, first found wins:

- **Capacitance**: the value field, else the library's `capacitance_f`. A class II dielectric and a voltage rating in the value (`10uF 6.3V X5R`) turn on the DC bias and aging estimates, as **Models from values** does.
- **ESL**: `PI_ESL`, else the library's `esl_h`, else the part's own from its package (about 0.4 nH for an 0402, 0.58 nH for an 0603). The solve adds the board's mounting inductance (pads, vias, planes) on top.
- **ESR**: `PI_ESR`, else the library's `esr_ohm`, else, for a ceramic chip capacitor (MLCC), a typical one's at its capacitance: about 30 mΩ at 100 nF, 12 mΩ at 1 µF and 5 mΩ at 10 µF. Real parts differ by about 2× either way, so each estimate is named in the log's notes. Polymer, tantalum and electrolytic parts (by footprint or value) and parts with no chip size in their footprint get no estimate.

A value still unknown is left at 0 (the model shows *values needed*), named in the notes, and offered as a library stub to fill in.

(parts-library)=
### The parts library, pi\_parts.yml

Numbers for a part kept once, for every copy of it on every board. KiPI-SI reads two files, when they exist: the user's, in `%APPDATA%\kipi_si\pi_parts.yml` (Windows) or `~/.config/kipi_si/pi_parts.yml` (Linux and macOS, or `$XDG_CONFIG_HOME/kipi_si`), then the project's, beside the board. For a part in both, the project's entry wins. The Auto-fill rail dialog shows which files it found.

A part is looked up by its manufacturer part number: the first of its `MANUFACTURER PART NUMBER`, `MPN`, `Manufacturer_Part_Number`, `Manufacturer Part Number`, `MFR PART NUMBER`, `MFN` or `PN` fields, else its value. A part's own PI\_ fields override its library entry.

```yaml
kipi_si_parts: 1
parts:
  LMH6518SQX/NOPB:                  # MPN, or the value field
    supplies:                       # as in a load model
      - {name: VA, pins: ['3', '4'], current_a: 0.23,
         tolerance: {min: -5, max: 5, unit: "%"}}
  BLM15PX121SN1D:                   # a ferrite bead
    link: {resistance_ohm: 0.055, current_max_a: 2.0}
  RC0402FR-070R1L:
    link: {power_max_w: 0.0625}     # its resistance from its value field
  TPS7A9101DSKR:
    vrm: {out_pins: ['1', '2'], voltage: 1.8, current_limit_a: 1.0}
  SIC431AED-T1-GE3:                 # a switcher, for Auto-fill power tree
    vrm: {kind: smps, fsw_hz: 600e3}
  GRM155R71C104KA88D:               # a capacitor, for AC
    cap: {capacitance_f: 100e-9, esl_h: 0.4e-9, esr_ohm: 0.03}
  TP-5000:
    role: ignore                    # load, link, vrm or ignore
```

- `supplies` are written as in a {ref}`load model <load-models>`: `current_a` or `pin_groups`, pins, ground pins and the tolerances. On a part with several supplies, each load takes the supply sharing the most pins with it, else the one whose name is in the load's name or net.
- `link`: `resistance_ohm`, `current_max_a`, `power_max_w`.
- `vrm`: its `out_pins`, `voltage` (else read from the rail's name, else 1 V with a note), `current_limit_a`, `kind` (`smps`, `ldo` or `source`, as `PI_VRM`) and `fsw_hz` (as `PI_FSW`). A part with a `vrm` entry comes early in the **Driven by** list.
- `cap`: `capacitance_f` (else read from the value field), `esl_h`, `esr_ohm`.

Unlike the fields, the library takes plain numbers in the base unit: `current_a: 0.23`, not `230mA`.

After an auto-fill that found parts with no current, resistance or capacitor values, KiPI-SI offers to add them to the project's `pi_parts.yml` with empty values, one entry per part number, to fill in once for every copy. Run **Auto-fill rail…** again after filling them. When the file's last section is not `parts:`, they go to `pi_parts.missing.yml` beside it instead, to copy in by hand.
