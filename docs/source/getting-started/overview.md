(overview)=
# What KiPI-SI does

KiPI-SI is a power integrity (PI) analyzer that runs as a KiCad 9/10 plugin. It reads the copper of your board straight from the PCB editor and simulates how power gets from your regulators to the parts that use it. It also runs {ref}`standalone <window>`, without KiCad, on board files. It has four analysis modes, chosen at the right end of the toolbar: DC, AC, Coupled Noise and {ref}`Signal Integrity <si-concepts>`.

:::{note}
**New to power integrity?** The {doc}`Solver Guide </theory/index>` explains what PI analysis is, why it matters, and how the mesh and the DC, thermal and AC solvers work.
:::

```{list-table}
:header-rows: 1
:class: kipi-table

* - Mode
  - Question it answers
  - What you get
* - **DC**
  - With every load drawing its current, what voltage actually reaches each pin, how much current flows through each trace, plane and via, and how hot does the board get?
  - IR drop and PASS/FAIL per load, voltage, current density, power density, via current and temperature maps in 3D, VRM and loss tables, an optional HTML report.
* - **AC**
  - Looking into a device's power pins, how does the impedance of the power distribution network (planes, vias, decoupling capacitors) vary with frequency, and is it below the device's target impedance?
  - |Z| versus frequency curves for each probe point, a cursor to read values off them, and PASS/FAIL against a flat or custom target mask.
* - **Noise**
  - How much of a switching regulator's noise couples onto nearby signal nets, and is it within each receiver's noise margin?
  - The switcher's waveforms, each victim's noise by mechanism, PASS/FAIL, and where it couples in 3D.
* - **SI**
  - Are the signal nets' impedance, return paths, crosstalk and stubs right, and does a channel's eye open at its interface's rate?
  - A Quick Scan of every signal net; for a channel, S-parameters, TDR, eyes with equalisation, COM, waveforms with IBIS or generic buffers, PASS/FAIL, Touchstone and SPICE export.
```

KiPI-SI infers nothing about your power system from the schematic. You tell it where the regulators are, what each load draws, which parts sit in series between nets, and (for AC) which capacitor model each decoupling capacitor uses. The board's copper, layer stackup, vias and pads come from KiCad.

:::{admonition} Accuracy
:class: warning

KiPI-SI's solvers are a 2.5D finite element model of the copper, checked against closed-form results. Solving the field is the well-understood part; the modelling of vias, regulators and parts is where the approximations are. Treat the results as an engineering estimate and sanity-check anything surprising.
:::
