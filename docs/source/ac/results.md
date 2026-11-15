(ac-results)=
# AC results

(ac-plot)=
## Impedance plot and cursor

The **Impedance** tab in the middle plots |Z| against frequency on log-log axes: one solid curve per probe and, dashed in the same color, its target. Hovering shows every probe's |Z| at the frequency under the mouse in the line above the plot.

```{figure} /images/ac_impedance.png
:alt: Impedance plot with a cursor and its values in the Info box

Impedance curves and targets, with the cursor's values in the Info box.
```

### Cursor

```{list-table}
:header-rows: 1
:class: kipi-table

* - Action
  - Input
* - Place on the nearest curve
  - Left-click
* - Move along the curve
  - Drag, or {kbd}`←` {kbd}`→` (with {kbd}`Shift`: 10 points)
* - Switch curve
  - {kbd}`↑` {kbd}`↓`
* - Remove
  - {kbd}`Esc` or right-click
```

The Info box shows the cursor's frequency, |Z|, phase, R and X, the reactance as an equivalent L or C, the target there with PASS/FAIL and the margin in dB (positive is below the target), and every other probe's |Z| at the same frequency.

**Screenshot…** in the toolbar saves the plot as a PNG while its tab is showing.

(ac-map)=
## Board map

The **Board map** tab shows the solve from above, as in the {ref}`HTML report <ac-report>`: the solver's mesh of the rail (copper colored) and its ground (blue-gray), the board outline, the probes as red stars, and the capacitors in the model as dots, one color per capacitor model. Capacitors between the rail and ground that have no model, and so are left out, are crossed. The view is fixed, always fitted to the board.

The map fills in while the rail solves: the parts as soon as the solve starts, then the mesh once it is built. The tab comes to the front for the solve; the **Impedance** tab comes back to the front when the results arrive.

```{list-table}
:header-rows: 1
:class: kipi-table

* - Control
  - Does
* - **Layer**
  - The copper layer whose mesh is shown, or **All layers** (the rail drawn over its ground).
* - **Mesh edges**
  - Draws the triangles' edges. Untick it to see the copper alone.
* - Hover a part
  - Its reference, value, side and capacitor model (C, ESL, ESR).
```

The map belongs to each rail's result, so switching **Rail** shows that rail's map, and saved results keep it. Results saved by KiPI-SI before 0.7.2 have no map.

```{figure} /images/ac_board_map.png
:alt: Board map of the core rail's mesh with the probe and capacitors

The Board map of the multiphase buck's core rail.
```

(ac-transient)=
## Transient

*The estimated response to each probe's load step*

The **Transient** tab estimates what the rail does at each probe that has a **Load step** and **slew rate**: the load steps up by ΔI, holds until the rail has settled, and steps back down. The top plot is the load current. The lower plot is the rail's deviation from its DC value: the **undershoot** when the load steps up and the **overshoot** when it steps back down. Each probe's step is worked out on its own, with the other probes drawing nothing extra. A circle marks each peak, and the legend gives them in mV. Dashed lines at ± target |Z| × ΔI show the AC tolerance a flat target stands for (Z{sub}`target` = V{sub}`AC` / ΔI).

How it is worked out: the AC solve gives the **open-loop** impedance, with the VRM out of circuit, and a step into that alone would never recover. So the converter's loop is closed again from its **Control loop bandwidth**: the VRM drives the rail from its voltage error with a typical proportional-integral compensation, crossing over at the bandwidth with about 60° of phase margin. Above the bandwidth the rail sees the PDN's own impedance; at DC the loop holds it exactly (the DC solve gives the DC value). The load current's spectrum times that closed-loop impedance, back in time, is the response. Only the bandwidth comes from your setup, so treat the result as an estimate. The converter's real compensation, its output impedance and any load-line will change the slow part, while the fast part (ESL, plane and via inductance, capacitor resonances) comes from the solve. A linear model mirrors itself, so the overshoot on release matches the undershoot on the step.

```{list-table}
:header-rows: 1
:class: kipi-table

* - Control
  - Does
* - **20 MHz limit**
  - Shows the rail as an oscilloscope with its 20 MHz bandwidth limit on would: through a single pole, 3 dB down at 20 MHz. Fast spikes and ringing shrink to what such a measurement sees, and so do the figures in the legend. The results table and the report keep the full bandwidth.
* - Toolbar
  - Zoom to a rectangle, pan, step back and forward, home. The fast edges last nanoseconds and the loop's recovery tens of microseconds, so zoom in to see the spikes.
* - Hover
  - The time, and each probe's load current and deviation there.
```

A probe with a load step but no VRM bandwidth gets no estimate, and a note says so. A note also flags a load step that rises faster than the time step or the sweep covers, and a rail that has not settled before the load steps back down.

(ac-table)=
## Results table and notes

```{list-table}
:header-rows: 1
:class: kipi-table

* - Column
  - Meaning
* - Min |Z|
  - Lowest impedance in the sweep.
* - Worst |Z| / at
  - With a target: the point where |Z| comes closest to, or furthest over, the target (within the target's frequency range). Without one: the highest |Z| in the sweep.
* - Target
  - The flat level, or the custom mask's range.
* - Undershoot / Overshoot
  - For a probe with a load step: the estimated dip when its load steps up and rise when it steps back down, at full bandwidth (see {ref}`Transient <ac-transient>`).
* - Verdict
  - {bdg-success}`PASS` if |Z| is at or below the target everywhere it applies.
```

Below the table, the notes give the rail's nets and ground, the number of capacitors and series links included, the total plane capacitance, the solve size and time, capacitors left out for having no model, and any warnings. **Export CSV…** writes |Z|, R and X of every probe at every frequency. **Export model** writes the selected probe as either sampled Touchstone Z1P or a fitted-pole HyperLynx PLS one-port file. Each probe is exported separately because the solve stores driving-point curves, not mutual impedances between probes. **Save results…** writes every rail solved so far to a `.kipi_si-ac-results` file (named with the board and the time by default); **Open results…** in AC mode brings them back, each under its VRM in **Rail**. Rails whose VRM is no longer in the setup are left out.

(ac-report)=
## AC report

**Report** writes `<board>_<rail>_ac_report_<date>_<time>.html` of the shown rail's results in the `kipi_si_reports` folder next to the board; the time stamp keeps every report. Like the DC report, it is a single offline file you can email. It holds:

- a summary and the probe table: pins, minimum and worst |Z|, the target, the margin in dB at the worst point (positive passes), PASS/FAIL, and an overall verdict;
- an interactive impedance plot of |Z| at every probe, with the targets dashed. Drag to zoom, double-click to reset, hover for f, |Z|, R and X. Click a legend entry to hide or show a curve. The grey dotted curves, hidden at first, are each capacitor model on its own (one part, without mounting), useful for matching dips to capacitor banks;
- a board map seen from the top: the board outline, the rail's copper on every layer merged, the probes as stars and each capacitor colored by its model. Capacitors left out for having no model show as grey crosses;
- for probes with a load step, the transient: a table of each load step, its slew rate and rise time, the undershoot and overshoot and ± target × ΔI, and the plot of the load current and the rail's deviation;
- the capacitor models (C, ESL, ESR, self-resonance, how many parts and which), the series links, the sweep, mesh and copper settings, and the solver's size, backend and time;
- notes: capacitors left out and any warnings.

With **PDF** chosen, the report is a `.pdf` with the same sections, the impedance plot and board map as images (probes and targets; no hover or per-model curves), and the User notes box as a form field to type in and save. If a PDF can't be made, KiPI-SI writes the HTML report instead and the log says why.

If the report can't be written, the log says why; the solve's results are kept either way.

(ac-reading)=
## Reading an impedance curve

- **Falling at −20 dB/decade** (|Z| ∝ 1/f): capacitive. At the low end this is the bulk capacitance; since the VRM is not modeled, the curve keeps rising toward low frequency.
- **Dips**: series resonances, where a capacitor bank's C and its ESL plus mounting inductance cancel. The depth is set by ESR.
- **Peaks** between dips: **anti-resonances**, where one bank's inductance resonates with the next bank's capacitance. These are usually where a target fails. Fix them with more or lower-ESL parts, more value overlap between banks, or extra damping (ESR).
- **Rising at +20 dB/decade** (|Z| ∝ f): inductive. The capacitors' ESL and their mounting (pad, via and spreading inductance) dominate. Place the cursor here: Info shows it as an equivalent inductance. Shorter, wider connections and more vias lower it.
- **Sharp peaks at high frequency**: plane-pair cavity resonances. Their frequencies come from the board's dimensions and stackup.
- **Phase** near −90° is capacitive, near +90° inductive, near 0° resistive.
