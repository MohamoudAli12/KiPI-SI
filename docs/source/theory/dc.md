(sg-dc)=
# DC: voltage drop

At DC, current in a copper sheet flows from high to low voltage, spreading out wherever the copper is wider. The voltage *V* on the sheet obeys

```{container} eq
∇·(G{sub}`s` ∇V) = 0, with sheet conductance G{sub}`s` = t / ρ
```

where *t* is the copper thickness and *ρ* its resistivity (1.72×10⁻⁸ Ω·m for copper at 20 °C). 1 oz copper (35 µm) has a **sheet resistance** of about 0.5 mΩ per square: any square of it, of any size, measures 0.5 mΩ edge to edge. A trace 0.2 mm wide and 20 mm long is 100 squares, or about 50 mΩ.

On each triangle the voltage is taken to vary linearly. That turns the equation into a small conductance matrix per triangle, like three resistors joining its corners. Adding them up gives one large sparse system **G·V = I**: the conductance matrix, the unknown node voltages, and the currents injected at the pads. Then:

- A **via or plated hole** joins the rim nodes on each layer it passes through, through its barrel's resistance *ρ·L / (π(d·t{sub}`p` − t{sub}`p`²))* for drill *d* and plating *t{sub}`p`*. A 0.3 mm via through 1.6 mm of board is about 1.3 mΩ.
- A **VRM output** holds its pads at its set voltage (a fixed node voltage).
- A **load** draws its current from its pads, shared equally between them or split into groups of pads with different current requirements.
- A **series part** (a sense resistor, load switch or a ferrite bead's DC resistance) joins the pads on both sides through its resistance, so the nets it joins are solved as one.

Solving gives the voltage at every node. The current density comes from the voltage gradient, the via currents from the barrels, and the power lost in the copper from *I²R* summed over every triangle and barrel.

(sg-dc-tree)=
## The power tree

Boards have more than one rail, and rails feed each other: a 12 V input feeds a buck to 3.3 V, which feeds an LDO to 1.8 V. KiPI-SI solves them downstream first:

- An **LDO** draws from its input what it delivers plus its quiescent current.
- A **switching regulator** draws *V{sub}`out`·I{sub}`out` / (η·V{sub}`in`)*. Its input voltage depends on the drop on the input rail, which depends on the current it draws, so KiPI-SI iterates the two until they agree.
- **Remote sense** moves a VRM's output until its sense pins sit at the set voltage, as the real control loop does. This creates voltage boost in some places, and drop in other places.
- **Ground** is a net like any other: loads return their current through their ground pins, so ground drops count too.

(sg-dc-tolerance)=
## Tolerance analysis

Each load can have a **tolerance**: how far its supply may sit from the nominal voltage, as ± percent or in volts, taken from the load's datasheet. After the solve, KiPI-SI checks every supply pin of the load. The worst pin's deviation from the VRM's set voltage (from DC drop on the rail, rise on ground, and a VRM load line if it has one) must be within the tolerance for the load to {bdg-success}`PASS`. Any pin outside it makes the load {bdg-danger}`FAIL`, and the result tables show which pin and by how much.

Tolerance analysis answers "does this layout leave the chip enough margin?" rather than "what is the voltage?". Two points matter when choosing the number:

- The datasheet tolerance covers *everything*, including the regulator's set-point accuracy and the AC ripple and droop. The DC drop may only use part of it. If a 1.0 V ±5% rail's regulator is ±1% accurate and you budget 2% for AC, the DC drop gets the remaining 2%: enter 2 for the load, not 5.
- The regulator tolerance, the ±1% in the above bullet, can be derived from feeedback resistor tolerances and the regulator's datasheet specifications for its reference voltage accuracy.
- Use the worst-case current, not the typical one, since drop scales with current. With electro-thermal on, the check uses the copper at its solved temperature, which is when its resistance is highest.

VRMs are checked too: whether the input left after the input rail's drop is still above the regulator's dropout and within its input range. A VRM that cannot hold its output fails every load downstream of it.
