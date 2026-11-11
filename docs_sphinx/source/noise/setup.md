(noise-setup)=
# Coupled Noise setup tabs

(noise-aggressors)=
## Aggressors

**Add** makes an aggressor for a switcher VRM and fills its phases from the board. The top of the form holds what all phases share:

- **VRM** and **Topology** (Auto from the voltages, or Buck or Boost). The line below shows the operating point: voltages, output current and duty cycle, or what is missing for one.
- **Input voltage** and **Output current**: blank uses the VRM's and the DC loads'.
- **Switching frequency**, **Rise time** and **Fall time** of the switch node. Phases are interleaved evenly, 360°/N apart.
- **Duty cycle**: blank computes it from the voltages, raised by the losses you enter.
- **Least ringing damping**: the hot loop's resistance alone barely damps a real switch node; its switches' output capacitance, reverse recovery and radiation take energy too, and measured ringing usually dies within five to ten cycles. The ringing is damped at least this much (ζ, default 0.05); 0 uses the loop's resistance alone.
- **Soft edge damping**: the least damping of the soft edge, the one the inductor current carries into a body diode's clamp (ζ, default 0.5: one overshoot, then settled). Set it to the least ringing damping to ring both edges alike.
- **Ripple at AC probes**: tick any of the AC setup's probes to see this aggressor's ripple there. The ripple is the voltage between the probe's rail and ground pins, from the board model, so the board model must be on. A probe has to be on the aggressor's input or output rail, or on a net that a series link joins to one; any other probe is noted and left out.

Below, one phase at a time: pick it in the phase list, or **Add phase** / **Remove phase**. **Fill from VRM** replaces the phases with one per VRM phase, read from the board: the switching device's pins from the VRM's, the inductor between the device and the rail, its value, the switch node, and the capacitors from each rail to ground, each given to the nearest phase. Each phase has:

- **Inductor**, **Inductance** and **DCR**.
- **Winding axis** and **Shielded inductor**: how the inductor's winding sits (vertical for a flat SMD drum or moulded part, along or across the part for one wound on a rod lying flat) and whether a shield closes its flux, for its stray field (see {ref}`the concepts <noise-concepts>`). An unshielded part's whole winding reaches the board around it; a shielded part's field is weaker and falls off sooner.
- **Switch node**: the net between the switching device and the inductor.
- **High-side pins** and **Low-side pins** ({ref}`pin pickers <pin-picker>`): the switching device's pins on the rail its hot loop is fed from (VIN for a buck, the output for a boost) and its power ground pins. A discrete design may name a different part for each.
- **Input capacitors** and **Output capacitors**: tick the capacitors on each rail this phase uses. The ripple current is shared among them by their impedances.
- **Coss**, **High-side Rds(on)** and **Low-side Rds(on)** from the datasheet, all optional: without them typical values are used and the ringing is approximate.
- **Qrr**: the reverse-recovery charge of the body diode the hard edge switches off (a buck's low-side FET, a boost's rectifier), from its datasheet. Not set: 5 nC, a low-voltage MOSFET's after a short dead time; enter 0 for a Schottky or GaN switch. More charge rings the hard edge higher.
- **Package inductance**: the loop inductance inside the device, added to the board's.

(noise-victims)=
## Victims

**Add** makes a victim of the first signal net not yet one, with its driver and receiver guessed as the net's two pads farthest apart. For each victim:

- **Net** and an optional **Name**.
- **Type**: what drives and loads the net. CMOS push-pull, open drain (held only by its pull-up), series or parallel terminated, a differential (LVDS) leg, a high-impedance analog input, or **High impedance (undriven)**: a tri-stated or floating net, held by nothing but its inputs' leakage. A type fills in the values below; editing them makes it Custom.
- **Driver pins** and **Receiver pins** ({ref}`pin pickers <pin-picker>`): where the trace is driven and where its noise is judged. Blank guesses them.
- **Driver resistance** (driving high, or an open drain's pull-up), **Driving low** (where it differs: an open drain's switch, 20 Ω; blank is the same as driving high), **Receiver resistance**, **Receiver capacitance** and **Termination** (a parallel termination at the receiver).
- **Logic level**: the family's supply. Held high, the line sits at the supply through the driver's resistance into the receiver and termination; held low, at ground. The noise margin is the smaller gap from those levels to the family's JESD8 VIH and VIL: 800 mV for lightly loaded 3.3 V CMOS. **Noise margin** overrides it, putting each threshold that far from its level.

With **PI Models** shown, each victim's driver and receiver pins are marked in orange in the 3D view ("*victim* driver", "*victim* receiver"; the guessed ones where they are not set). Selecting a victim highlights both; clicking either marker selects the victim.

(noise-caps)=
## Capacitors

The same capacitor models as {ref}`AC mode <ac-caps>`, edited here too. A ticked capacitor without a model is taken at its value from the board with a typical ESR and ESL, and the results say so.

(noise-settings)=
## Settings

- **Highest frequency**: the highest harmonic kept. Blank: ten times the faster edge's corner frequency, 1/(π·rise time), or three times the ringing, at most 3 GHz.
- **Harmonic limit**: the most harmonics of the switching frequency kept.
- **Dead time**: how long the inductor current has to carry a soft edge across (default 20 ns). A soft edge that would take longer (C\_sw·V/I, at light load) is finished hard by the next switch, at the entered edge time. 0 lets the current take as long as it needs.
- **Periods shown** in the waveform plot.
- **Victim segment**: victim traces are cut into pieces this long, each with its own cross-section of the copper around it (default 0.5 mm).
- **Coupling window**: how far either side of a victim trace copper is taken into its cross-section (default 3 mm). Switch-node copper further away does not couple.
- **Board model**: solve the rails and ground's copper (above), and trace the hot loops through it. Off, the capacitors share the current by their own impedances, the hot loops are drawn straight between the pads and there is no shared-ground coupling.
- **Field solves per decade**: copper solves per decade of the harmonics; the board's response in between is interpolated (default 10). Where it is not smooth (the planes' cavity resonances) the copper is solved at the harmonics themselves as well.
- **Scan radius**: the scan looks at signal nets with a trace this close to the aggressor's parts (default 10 mm). **Scan: solve in full**: how many of the worst estimates are solved in full (default 10). **Scan: victim type** and **logic level**: what scanned nets are solved as and judged with, as their real drivers are not known. The default type, **High impedance (undriven)**, is the worst case for capacitive coupling. A net that is a victim already keeps its own type. **Custom driver** uses **Scan: driver resistance** instead.
