# Introduction to power integrity

(sg-pi)=
## What power integrity is

Every chip on a board needs its supply voltage held within a tolerance, typically a few percent, whatever current it draws. A voltage regulator (VRM) sets that voltage, but the chip does not sit at the regulator's pins: between them is the **power distribution network (PDN)**, made of traces, planes, vias, the capacitors around the chip and the copper that carries the current back to ground.

That copper is not a perfect conductor. It has resistance, so a steady current drops voltage along the way, and it has inductance, so a current that changes quickly drops voltage too. **Power integrity (PI)** analysis predicts those drops and checks that what arrives at each chip is still in tolerance:

- **DC**: the steady drop from resistance, *V = I·R*, and the heat the current makes in the copper.
- **AC**: the drop from a changing current, set by the PDN's impedance across frequency, *ΔV = Z(f)·ΔI*.

The whole budget is shared: a 1.0 V rail with ±3% tolerance has 30 mV to spend, split between the regulator's own accuracy, the DC drop and the AC ripple and droop.

(sg-why)=
## Why it matters

Supply voltages have fallen while currents have risen. A processor core at 0.8 V and 40 A has a total tolerance of about 25 mV. At that current, a single milliohm of copper uses 40 mV, more than the whole budget. A rail that is out of tolerance rarely fails cleanly. Instead it causes intermittent resets, bit errors, jitter on clocks and serial links, and failures that come and go with temperature or workload. These faults are hard to find on the bench and expensive to fix with a respin.

The layout decides most of the PDN, through plane shapes, neck-downs, via counts and where the capacitors go. PI simulation looks at it before fabrication, while fixing a problem means moving copper rather than adding bodge wires.

(sg-analyses)=
## What KiPI-SI simulates

```{list-table}
:header-rows: 1
:class: kipi-table

* - Analysis
  - Answers
  - Results
* - DC voltage drop
  - Does every load get enough voltage at its full current? Which copper and vias carry the most current?
  - Voltage, current density and power density on every layer in 3D, current in every via, the voltage at every load pin, copper losses, and PASS/FAIL per load, VRM and via.
* - Electro-thermal (optional, with DC)
  - How hot does the copper get, and how much does that raise its resistance and the drop?
  - Board temperature map, the hottest copper per layer, and the DC results at that temperature.
* - AC PDN impedance
  - How stiff is the supply seen by a chip, from kHz to hundreds of MHz? Does it meet the chip's target impedance?
  - |Z|, R and X at each probe over frequency, against flat or custom targets, with each capacitor model's own curve.
* - Coupled Noise
  - How much of a buck or boost converter's switching noise reaches nearby signal nets, through which path, and is it within the receiver's noise margin?
  - The converter's switch-node, inductor, capacitor and ripple waveforms; its hot-loop inductance and ringing; each victim's noise at its receiver over time and frequency, split by mechanism, with PASS/FAIL against its noise margin; a ranked scan of the nets near the converter.
```

All four use the same model of the board: the copper of each net on each layer, read from KiCad (or a board file), the stackup's thicknesses and materials, and a **power tree** you describe once. The power tree says which pads are VRM outputs, which are loads and what they draw, and which parts (sense resistors, ferrite beads, load switches) join one net to another.
