(dc-results)=
# DC results

The **Results** box under the Solve button. Pick a **net group** and a **field** to color the copper in 3D.

(dc-fields)=
## 3D result fields

```{list-table}
:header-rows: 1
:class: kipi-table

* - Field
  - Shows
  - Look for
* - Voltage (V)
  - Copper potential.
  - The gradient from VRM to load; where the drop happens.
* - Current density (A/mm²)
  - How hard the copper is worked. Tick **Arrows** to see where and which way current flows: flat white arrows drawn on each layer's copper, top and bottom faces, longer where the current is denser.
  - Necks, thermal reliefs, narrow traces, plane slots. Clipped at the 99.5th percentile (pad corners spike).
* - Power density (mW/mm²)
  - Copper loss per area.
  - Hot spots that the thermal solve will pick up.
* - Via current (mA)
  - Current in each via barrel.
  - Vias doing all the work while neighbors idle.
* - Temperature (°C)
  - Each layer's copper temperature (electro-thermal only).
  - Peak location and rise.
```

**Show copper** returns to the plain geometry; pick a group or field again to bring the results back. Click anywhere to probe: Info shows the exact value at that point (not clipped).

(color-scale)=
**Color scale**: the minimum and maximum of the colors, under the group and field. Each result starts on its whole range, over every layer whether shown or not. Type limits (or step them with the arrows) to stretch the colors over the part you care about; values outside take the end colors. Limits are kept for each net group and field until **Auto** fits the whole range again; temperature limits apply to every group, so an ambient-to-limit scale stays put while you switch groups. On the logarithmic power-density scale, a minimum of zero or below falls back to four decades below the maximum.

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item}
```{figure} /images/voltage.png
:alt: Voltage across a plane

Voltage.
```
:::

:::{grid-item}
```{figure} /images/current_density.png
:alt: Current density with arrows

Current density with arrows.
```
:::

:::{grid-item}
```{figure} /images/via_current.png
:alt: Via current

Via current and the Vias table.
```
:::

:::{grid-item}
```{figure} /images/temperature.png
:alt: Board temperature

Temperature from the electro-thermal solve.
```
:::

::::

(dc-tables)=
## Results tables

*Click a header to sort; again to reverse*

The **Voltages** list beside the tabs picks how the Loads and VRMs tables show their voltages: in **mV from target** (the default), in **% from target** or in **Volts**. The target is the regulated voltage of the VRM driving the rail. From the target, negative is a drop below it and positive a boost above it. The web report has the same list at its top; a PDF report shows each voltage in all three.

```{list-table}
:header-rows: 1
:class: kipi-table

* - Tab
  - Columns and use
* - **Loads**
  - Current; the mean effective voltage (supply − ground); the lowest and highest supply pins; the tolerance; the **margin**, how far the pins are inside the tolerance (negative when outside, in red); and the verdict. Double-click a row to show its group.
* - **VRMs**
  - V out, I out, V/I in, input power, conversion loss, the rail's lowest voltage anywhere on its copper, current limit and PASS/FAIL; a gray row per phase under multi-phase VRMs.
* - **Series links**
  - Resistance, current and power in each part.
* - **Vias**
  - Every via and PTH barrel, highest current first. The **Current limit** for PASS/FAIL starts at 1 A, a placeholder; set your own, or 0 for none. Double-click a row to fly the camera to it.
* - **Losses**
  - Copper loss per group and layer, in vias and series parts, with the total and each VRM's conversion loss at the bottom.
* - **Thermal**
  - After an electro-thermal solve: the hottest copper on each layer, at that layer's own temperature, its rise and location, PASS/FAIL against the limits, the iteration history and the dielectric conductivities used, in-plane and through. Double-click a row to show its group's temperature.
* - **Notes**
  - Solve time, the nets in each group, pin group results, warnings and excluded groups.
```

### Load verdicts

```{list-table}
:header-rows: 1
:class: kipi-table

* - Verdict
  - Meaning
* - {bdg-success}`PASS`
  - Every supply pin within the tolerance.
* - {bdg-danger}`FAIL`
  - At least one pin outside the tolerance.
* - {bdg-danger}`VRM OUT OF REGULATION`
  - A VRM feeding it, directly or upstream, is outside its input range or below its dropout.
* - {bdg-warning}`NOT CONVERGED`
  - Its group's solve did not converge; the numbers cannot be trusted. See {ref}`Troubleshooting <troubleshooting>`.
* - {bdg-warning}`DISCONNECTED`
  - None of its supply pins, or none of its ground pins, has a copper or series-link path to its VRM, so its current was left out of the solve. The Notes tab names the pins. See {ref}`Loads not connected by copper <ts-no-path>`.
* - (blank)
  - No tolerance set.
```

(dc-reading)=
## Reading the numbers

- **Effective voltage** is what the load actually sees: its supply pins minus its ground pins. Compare it with the regulated voltage, not the raw plane voltage.
- A supply plane reading *above* its regulated voltage is normal with remote sense or when ground return is solved; see {ref}`drop and boost <dc-concepts>`.
- The **lowest and highest pins** are what pass or fail a load; with many pins, one far pin can fail a load whose mean looks fine. The **margin** says how close the nearer one is to its tolerance.
- The color scale covers the whole result; type a minimum and maximum under it to look closer.
- Losses are I²R in the copper; VRM conversion loss is the difference between input and output power.

(dc-export)=
## Export and HTML report

```{list-table}
:header-rows: 1
:class: kipi-table

* - Export ▾ item
  - Writes
* - Tables as CSV…
  - One CSV per results table into a folder, plus `<name>_pins.csv`: every pin each group was solved with, and its voltage and current.
* - 3D results for ParaView (.vtm)…
  - The result meshes, for ParaView or other VTK tools.
* - Save results…
  - A `.kipi_si-dc-results` file, or `.kipi_si-dc-thermal-results` after an electro-thermal solve, that **Open results…** reloads without solving, named with the board and the time by default. It holds JSON and NumPy arrays in a zip, which open on any computer and cannot run code, so it is safe to share; the 3D views are rebuilt when it opens.
```

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item}
```{figure} /images/report_tables.png
:alt: HTML report tables

HTML report: summary tables.
```
:::

:::{grid-item}
```{figure} /images/report_3d.png
:alt: HTML report 3D view

HTML report: interactive 3D.
```
:::

::::
