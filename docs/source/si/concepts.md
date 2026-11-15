(si-concepts)=
# Signal Integrity concepts

**Signal Integrity** mode (**Ctrl+4**) checks how signals travel along the board's traces. It works at two levels:

- The **Quick Scan** looks at every signal net at once, for the layout faults that spoil signals: impedance off target, too much coupling to a neighbour, a trace with no reference plane under it or crossing a gap in one, a layer change with no return via near it, a via stub that resonates in band, and skew within a pair.
- A **channel** is one net or differential pair from a driving part to a receiving one, through any series resistors and AC-coupling capacitors. Solving it gives what a commercial SI tool would: S-parameters, TDR, eye diagrams with equalisation, COM, and waveforms with real (IBIS) or generic buffers, each checked against its interface.

**How it is modelled.** Each trace is cut into short sections. At each, a 2D finite element field solve of the cross-section (the trace, its neighbours within the window, the planes and every dielectric layer, solder mask included) gives the per-unit-length R, L, G and C matrices: the capacitance from the field, the inductance from the field without dielectric, the dielectric loss from a wideband (Djordjevic-Sarkar) model of each laminate fitted at its datasheet frequency, and the conductor loss from the surface charge (Wheeler's rule) with skin effect and the copper's roughness. Each section is a coupled lossy transmission line. Each via is a chain of barrel inductance and pad-to-plane capacitance (from an axisymmetric field solve), with its stub, and its return current between the planes: the plane pair's impedance matrix of all the channel's vias, with the stitching vias near them shorted, or, where the two planes are of different nets (ground and a supply), the capacitors joining those nets nearest them, each ended in its capacitance, ESR and 1 nH of inductance with its mounting. A pair's two vias are coupled through the planes they share, and without stitching the cavity resonates. The sections, vias, series parts and the buffers' packages make one circuit, solved over frequency.

**From S-parameters to eyes.** With the interface's source and termination resistances and the receiver's capacitance at the ports, the channel's transfer function gives its response to one bit (the pulse response). The **statistical eye** adds up every pattern of the neighbouring bits, the interface's random and deterministic jitter and noise, and each aggressor's crosstalk, to the target bit error ratio (BER). The equaliser (the transmitter's FFE presets, the receiver's CTLE and DFE) that opens it most is found by search. **COM** (channel operating margin) is the eye's main cursor over its noise at the target BER, in dB: 3 dB or more passes. The **transient** runs the buffers' own (IBIS or generic) I-V and switching curves at the ports through the channel's S-parameters, for overshoot, ringback and edge shape.

:::{admonition} Accuracy
:class: warning

the cross-sections agree with closed forms within about 2 % (microstrip and stripline impedance) and their loss with Wheeler's rule within about 3 %. Vias and discontinuities are approximations.
:::
