(sg-thermal)=
# Electro-thermal co-simulation

The power lost in the copper, *I²R*, turns into heat. On a high-current rail that heat raises the board temperature by tens of degrees, and the heat from neighboring planes, regulators and loads adds to it. KiPI-SI's thermal model spreads that heat across the whole board, with a temperature for each copper layer *l*:

```{container} eq
∇·(G{sub}`l` ∇T{sub}`l`) + Σ{sub}`m` (T{sub}`m` − T{sub}`l`) / R{sub}`lm` − (T{sub}`l` − T{sub}`amb`) / (1/h + R{sub}`coat`) + q″{sub}`l` = 0
```

- *G{sub}`l`* is how well layer *l* spreads heat sideways: its copper (weighted by how much of each spot is copper, on any net) plus half the in-plane conductivity of each dielectric it touches, from its material in the stackup.
- *R{sub}`lm`* is the resistance through the laminate to the neighboring copper layers *m* above and below, from each dielectric's through-plane conductivity. Glass laminates conduct about half as well through their thickness as along it (FR4 core 0.3 W/m·K against 0.8). Every plated hole, via or component hole, on any net, adds its barrel's copper in parallel, which is why thermal vias work.
- *h* is the convection to the air, about 10 W/m²K in still air (with radiation) and rising with the airflow you set. Only the top and bottom layers touch the air.
- *R{sub}`coat`* is the solder mask and silkscreen over an outer layer, in series with the air: *t*/*k* for each, a mask at 0.25 W/m·K over the whole face and a silkscreen at 0.2 in the cells where it prints (read from the board, usually a few percent of it). It matters little: a 25 µm mask is 0.1 K·mm²/W, against 100 K·mm²/W (1/h) from the surface into still air.
- *q″{sub}`l`* is the heat put into layer *l*: each layer's copper loss, via losses shared by the layers the via spans, and the heat of series parts, VRMs and, optionally, loads on the layers of their pads.

Spread out, the layers sit within a degree or two of each other: across 1.6 mm of FR4 the resistance is about a tenth of the resistance from the surface into the air. Concentrated, they do not. A regulator on the top layer heats its own pads and the top copper around it; the planes below see that heat only after it crosses the laminate or goes down vias. KiPI-SI reports each layer's own peak.

(sg-thermal-copper)=
## Hot copper resists more

Copper's resistivity rises with temperature, by about **0.393% per °C** near room temperature:

```{container} eq
R(T) = R{sub}`20` · (1 + α (T − 20 °C)), α ≈ 0.00393 /°C
```

Copper that runs 50 °C hotter than 20 °C has about 20% more resistance, and at 100 °C about 31% more. The physics behind it: as the copper heats, its atoms vibrate harder and scatter the electrons carrying the current more often.

That forms a loop: current heats the copper, the heat raises its resistance, more resistance means more drop and more *I²R* loss, and that loss heats it further. KiPI-SI's co-simulation follows the loop:

1. Solve the DC power tree at the current temperature map (20 °C everywhere at first).
2. Gather every loss on the board onto one grid, on the layer it is made on, and solve each layer's temperature.
3. Set each triangle's resistivity from its own layer's temperature where it sits, and go back to step 1.

Each pass reports how much the peak temperature changed. On most boards it settles within a few passes, which is when DC drop and temperature agree. A rail that keeps heating from pass to pass is a warning in itself: its copper is too narrow for its current.

The temperature coefficient can be set per layer in the Stackup window, for conductors other than copper.
