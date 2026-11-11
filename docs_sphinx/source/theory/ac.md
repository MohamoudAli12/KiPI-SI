(sg-ac)=
# AC: PDN impedance

(sg-ac-impedance)=
## What PDN impedance is

Chips draw current in bursts: a processor that wakes up, an FPGA's clock that starts, an amplifier at full swing. The regulator's control loop corrects slowly, typically within tens or hundreds of kHz, so faster changes in current are supplied by the capacitors and the planes. How much the voltage moves for a given change in current depends on frequency:

```{container} eq
ΔV(f) = Z(f) · ΔI(f)
```

**PDN impedance** *Z(f)* is the impedance a chip sees looking out of its power pins into the power supply network. It is the ratio of voltage change to current change, and it depends on every capacitor, plane and via between them and ground. It is a complex number at each frequency: KiPI-SI shows its magnitude |Z| and its resistive and reactive parts.

```{raw} html
<figure class="kipi-svg">
<svg aria-label="Sketch of PDN impedance against frequency: a target line, and a curve that dips at each capacitor's resonance with peaks between" role="img" viewbox="0 0 640 250" width="100%">
<line class="svg-axis" x1="60" x2="60" y1="20" y2="210"></line>
<line class="svg-axis" x1="60" x2="620" y1="210" y2="210"></line>
<text class="svg-label" text-anchor="middle" transform="rotate(-90 20 115)" x="20" y="115">|Z| (log)</text>
<text class="svg-label" text-anchor="middle" x="340" y="240">frequency (log)</text>
<line class="svg-target" x1="60" x2="620" y1="130" y2="130"></line>
<text class="svg-label" text-anchor="end" x="616" y="124">target</text>
<path class="svg-curve" d="M70 200 C110 180 140 150 160 150 C185 150 190 175 210 175 C230 175 240 110 265 105 C290 100 300 170 320 170 C345 170 355 120 380 112 C405 105 420 168 440 168 C460 168 470 95 500 80 C540 60 580 40 615 30"></path>
<text class="svg-label" text-anchor="middle" x="150" y="196">bulk</text>
<text class="svg-label" text-anchor="middle" x="320" y="190">MLCCs</text>
<text class="svg-label" text-anchor="middle" x="440" y="188">plane</text>
<text class="svg-label" text-anchor="middle" x="265" y="96">anti-resonance</text>
<text class="svg-label" text-anchor="end" x="570" y="28">package and via inductance</text>
</svg>
</figure>
```

```{container} figcaption
A typical PDN curve. Each group of capacitors pulls the impedance down near its resonance. Where one group hands over to the next, an inductance meets a capacitance and the impedance peaks (an anti-resonance). Above the plane's range, inductance wins.
```

A real capacitor is not a pure capacitance. It also has an equivalent series inductance (ESL, from its construction, termination, and mounting) and resistance (ESR). These factors vary greatly from capaitor to capacitor and case size to case size. Below its self-resonant frequency it acts as a capacitor and its impedance falls with frequency. Above it, it acts as an inductor and its impedance rises. That is why a PDN uses many values: bulk capacitors for low frequencies, many small ceramics for the middle, and the plane pair's own capacitance for the top. Where one hands over to the next, the curve has peaks (anti-resonances), and those peaks are where a rail is most likely to fail.

(sg-ac-target)=
## Target impedance

If the voltage may move by *ΔV* while the load steps by *ΔI*, the PDN must stay below the **target impedance**

```{container} eq
Z{sub}`target` = ΔV / ΔI
```

up to the highest frequency in the step. A 1.0 V rail allowed 3% (30 mV) of transient for a 10 A step needs Z{sub}`target` = 3 mΩ. A step that rises in time *t{sub}`r`* has most of its energy below *f ≈ 1 / (π·t{sub}`r`)*, which is how far the target applies. KiPI-SI's target calculator works both out from the load's transient spec (after Smith et al., 1999). Some chip vendors publish a frequency-dependent target mask instead, which KiPI-SI takes as corner points.

KiPI-SI leaves the regulator out of the AC model and computes the **open-loop** PDN impedance. Below the regulator's control-loop bandwidth, the loop is assumed to hold the voltage. Above it, the loop is too slow, which is the range a target applies to, so you give each VRM's bandwidth and the targets are judged from there up. Other analysis methods can model the interaction with the control loop and the capacitive portion of hte PDN, this is called **closed-loop** analysis and is outside the scope of KiPI-SI.

(sg-ac-model)=
## How KiPI-SI models it

The AC solver uses the same triangle mesh, extended for the fields between rail and ground copper:

- **Two faces per sheet.** At high frequency, current crowds onto the copper surfaces (the skin effect: about 6.6 µm deep at 100 MHz) and onto the face looking at the return current. Each copper sheet therefore has a top and a bottom face, joined at its edges, holes and pads, and the copper's internal impedance moves from its DC resistance to surface resistance with frequency.
- **Inductance.** A face looking at ground copper a distance *h* away has a loop inductance of μ₀*h* per square, 126 pH per square for 0.1 mm of dielectric. Thin dielectrics between power and ground keep the inductance low.
- **Capacitance.** Facing rail and ground copper is a capacitor of ε₀ε{sub}`r`·area / *h*, with the dielectric's loss tangent. 100 cm² of 0.1 mm FR4 is about 3.8 nF, a small capacitor of very low inductance that matters at hundreds of MHz.
- **Vias** join the faces of each layer through their barrels. Their inductance, and the inductance of a capacitor's mounting, comes out of how current spreads to them on the planes. You enter only each capacitor's own self ESL, not its mounting.
- **Capacitors** are series RLC models at their pads. A ferrite bead or resistor between nets is a series link and can include DCR and ESL.

For two facing planes this is the classic plane-pair (cavity) model, so plane resonances come out of the mesh, as does the spreading inductance between a capacitor and the chip. The sweep factorizes the copper model at a few frequencies per decade, solves for every capacitor and probe port at once, interpolates that smoothly, and adds the capacitors at each of the many frequencies plotted. This keeps a sweep from 1 kHz to 300 MHz at a few hundred points per decade fast. Note this this creates a massive computational problem. AC solves can take a long time.

(sg-ac-capacitance)=
## Effective vs nominal capacitance

The capacitance printed on a ceramic capacitor (MLCC) is measured at 1 kHz, 25 °C, with no DC voltage, when the part is new. On a board it is often much less. KiPI-SI uses the capacitance you enter for each model, so enter the **effective** value at your rail's conditions. Four effects stack up:

```{list-table}
:header-rows: 1
:class: kipi-table

* - Effect
  - What happens
  - Typical size
* - Dielectric
  - Class I dielectrics (C0G/NP0) are stable. Class II (X7R, X5R, X6S) use barium titanate, whose very high permittivity depends on temperature, voltage and time. The code gives the temperature range and the allowed change across it. Class III (Y5V, Z5U) varies far more.
  - C0G: ±30 ppm/°C. X7R and X5R: ±15% over their range. Y5V: +22% / −82%.
* - DC bias
  - A DC voltage across a class II dielectric aligns its ferroelectric domains, which then respond less to the AC signal, so the permittivity falls. Small cases and low voltage ratings have thinner layers, a stronger field at the same voltage, and lose the most. C0G does not have this effect.
  - Often −30% to −80% at the rated voltage. A 10 µF 0402 6.3 V X5R part can keep under half its capacitance at 3.3 V. Good design practice dictates that a cap should only be exposed to half its rated voltage, for both safety factor purposes and to minimize DC bias impact.
* - Aging
  - After a class II part last cooled through its Curie point (about 125 °C, as in reflow), its domains slowly relax and its capacitance falls logarithmically with time: the same loss each decade of hours. Heating above the Curie point resets it ("de-aging").
  - X7R: about 1–2% per decade hour. X5R: about 3–5%. That is roughly 5–15% after a few years in the field.
* - Manufacturing tolerance
  - Parts are sold within a tolerance of the nominal value, coded by a letter (K = ±10%, M = ±20%).
  - −10% or −20% at the low end.
```

The effects multiply. A worst case for that 10 µF X5R part on a 3.3 V rail at 85 °C:

```{container} eq
10 µF × 0.45 (DC bias) × 0.85 (temperature) × 0.92 (aging) × 0.80 (tolerance) ≈ 2.8 µF
```

More than two thirds of the capacitance is gone. Lower capacitance raises the impedance below the part's resonance and moves the resonance up, by the square root of the ratio, while the inductance above resonance does not change. Capacitor makers publish DC-bias and temperature curves per part, and their online tools (Murata SimSurfing, TDK SEAT, KEMET K-SIM, Samsung's tool) give the capacitance, ESR and ESL at a chosen bias and temperature. Enter the manufacturer's delectric, tolerance, aging and DC bias factors. KiPI-SI can work out how each impacts the PDN impedance.
