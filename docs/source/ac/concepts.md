(ac-concepts)=
# AC concepts

## What the AC analysis models

The AC analysis computes the **PDN impedance** seen from a **probe**, a device's supply and ground pins, looking out into the board over a range of frequencies. A device that draws a changing current *I* from a PDN of impedance *Z* sees its supply move by about *I*·|*Z*|, so keeping |Z| below a **target impedance** keeps the supply ripple within tolerance.

A solve covers one **rail** (the nets its VRM drives, plus nets joined to them by series links) against one **ground** net. It includes:

- **The copper**, field-solved: plane and trace resistance (with skin effect), the spreading inductance of planes, the capacitance between facing rail and ground copper, cavity resonances, and the inductance of vias and their mounting.
- **Capacitors** between the rail and ground, each as a series R-L-C from its {ref}`model <ac-caps>`. Only the part's own ESL is entered; its mounting (pads, vias, planes) is simulated.
- **Series links** as their resistance plus ESL.

:::{note}
the VRM itself is not modeled as an impedance. In AC, VRMs only define which nets make up a rail and its default ground. Below the frequency where the capacitors take over, the real PDN impedance is set by the regulator's control loop, which the plotted curve does not include: expect the curve to rise toward low frequency as the bulk capacitance runs out.
:::

Capacitors that sit between the rail and ground but have no model are left out, and the results notes list them.
