(sg-noise)=
# Coupled Noise: a switcher as aggressor

A buck or boost converter switches amps in nanoseconds. Its switch node swings the full input (buck) or output (boost) voltage on every edge, and its hot loop carries a pulsed current. Both reach nearby signal nets: the switch node's electric field through mutual capacitance (a current C{sub}`m`·dV/dt), its loop's magnetic field through mutual inductance (a voltage M·di/dt), and the shared ground through common impedance. The victim is far weaker than the aggressor, so the problem is solved one way (weak coupling): the converter's waveforms are built first, and each coupling path then acts on the victim as a source, harmonic by harmonic. The noise from each path is kept apart, so the dominant one shows.

```{raw} html
<figure class="kipi-svg">
<svg aria-label="Sketch of a buck converter beside a victim net: the switch node couples through mutual capacitance, the hot loop through its magnetic flux, and the switching current's return through the shared ground" role="img" viewbox="0 0 680 280" width="100%">
<ellipse class="svg-target" cx="220" cy="150" fill="none" rx="78" ry="104"></ellipse>
<rect class="svg-cu" height="10" width="410" x="150" y="40"></rect>
<rect class="svg-pad" height="30" width="40" x="110" y="30"></rect>
<rect class="svg-pad" height="30" width="40" x="560" y="30"></rect>
<text class="svg-label" text-anchor="middle" x="130" y="22">driver</text>
<text class="svg-label" text-anchor="middle" x="580" y="22">receiver</text>
<text class="svg-label" text-anchor="middle" x="440" y="34">victim net</text>
<rect class="svg-cu" height="18" width="180" x="240" y="110"></rect>
<text class="svg-label" text-anchor="middle" x="380" y="146">switch node</text>
<rect class="svg-pad" height="38" width="40" x="200" y="100"></rect>
<text class="svg-label" text-anchor="middle" x="220" y="123">FETs</text>
<rect class="svg-pad" height="34" width="50" x="420" y="102"></rect>
<text class="svg-label" text-anchor="middle" x="445" y="123">L</text>
<rect class="svg-pad" height="26" width="40" x="200" y="168"></rect>
<text class="svg-label" text-anchor="middle" x="220" y="186">Cin</text>
<rect class="svg-curve" height="112" rx="18" stroke-dasharray="5 4" width="80" x="180" y="92"></rect>
<text class="svg-label" x="304" y="214">hot loop, i<tspan dy="3" font-size="9">HS</tspan></text>
<line class="svg-axis" x1="320" x2="320" y1="50" y2="77"></line>
<line class="svg-axis" x1="308" x2="332" y1="77" y2="77"></line>
<line class="svg-axis" x1="308" x2="332" y1="84" y2="84"></line>
<line class="svg-axis" x1="320" x2="320" y1="84" y2="110"></line>
<text class="svg-label" x="340" y="85">1 · capacitive: i = C<tspan dy="3" font-size="9">m</tspan><tspan dy="-3">·dV/dt</tspan></text>
<text class="svg-label" text-anchor="end" x="122" y="144">2 · inductive:</text>
<text class="svg-label" text-anchor="end" x="122" y="160">v = M·di/dt</text>
<rect class="svg-cu" height="8" width="490" x="110" y="236"></rect>
<line class="svg-axis" x1="130" x2="130" y1="60" y2="236"></line>
<line class="svg-axis" x1="580" x2="580" y1="60" y2="236"></line>
<line class="svg-axis" x1="220" x2="220" y1="194" y2="236"></line>
<line class="svg-axis" stroke-dasharray="3 3" x1="445" x2="445" y1="136" y2="236"></line>
<text class="svg-label" x="604" y="244">ground</text>
<text class="svg-label" text-anchor="middle" x="355" y="266">3 · common impedance: ΔV between the driver's and receiver's grounds</text>
</svg>
</figure>
```

```{container} figcaption
The three paths KiPI-SI models. The switch node's swing pushes charge onto the victim through their mutual capacitance (1); the hot loop's changing current links flux through the loop the victim makes with its return (2); and the switching current's return through the ground copper moves the driver's ground against the receiver's (3).
```

(sg-noise-flow)=
## How a solve runs

One converter, the **aggressor**, is solved at a time, against every victim set up for it (and, with the scan on, the worst of the nets near it). A solve takes these steps, and the log reports each:

1. **Operating point.** The input and output voltages come from the VRM (or your override) and decide buck or boost; the output current is what the DC loads on the output rail draw, unless you set it.
2. **Hot loop.** Each phase's loop through its input (buck) or output (boost) capacitors is traced on the copper, giving its inductance, resistance and the switch node's capacitance, and so the frequency and damping of the ringing on every edge.
3. **Waveforms.** The switch-node voltage, inductor current, pulsed current and each capacitor's ripple current are built as spectra of harmonics of the switching frequency, ringing included. They are shown at once, before any coupling is solved.
4. **Board model** (optional). AC mode's field model of the rails and ground shares the ripple current among the capacitors through the real copper, and gives the ground voltage between each victim's ends.
5. **Scan** (optional). Every signal net near the converter is estimated cheaply and the worst are added as victims of the scan's type, undriven by default.
6. **Victims.** For each one, the coupling to its traces is extracted (mutual capacitance by 2D field cuts, mutual inductance by PEEC), its line is solved at every harmonic once per mechanism, and the result is turned back into a waveform at the receiver and checked against its noise margin.

Because the coupling is weak, each step only feeds the next: the victims never load the converter, and each mechanism can be solved and judged alone. The sections below follow the same order.

(sg-noise-waveforms)=
## The aggressor's waveforms

From the input and output voltages, the duty cycle is D = V{sub}`out`/V{sub}`in` for a buck (raised by its losses) and 1 − η·V{sub}`in`/V{sub}`out` for a boost. Each phase's switch node is a trapezoid with the entered rise and fall times, its inductor current a triangle of ripple ΔI = (V{sub}`in` − V{sub}`out`)·D/(L·f{sub}`sw`) (buck) or V{sub}`in`·D/(L·f{sub}`sw`) (boost), and its pulsed current the inductor current while the hot-loop switch conducts (plus the ringing's current, below). These are piecewise linear, so their Fourier series is exact in closed form: the second derivative is a set of impulses at the corners, and c{sub}`k` = −1/(T·ω{sub}`k`²)·Σ Δs{sub}`i`·e{sup}`−jωkti`. N phases are interleaved by delaying phase n by n·T/N, which cancels every harmonic but each N-th in their sum. The harmonics run up to ten times the faster edge's corner frequency, 1/(π·t{sub}`r`), where the trapezoid's spectrum has fallen 40 dB/decade.

The ripple current into each rail's capacitors is shared by their admittances, each capacitor's model plus its loop's inductance and resistance; the rail's ripple voltage is that current through the bank's impedance.

(sg-noise-hotloop)=
## Hot loop and ringing

Each capacitor's loop through the switching device is drawn between their pads, as wide as the net's copper along each straight piece, and its inductance is the sum of the pieces' partial inductances (Ruehli's PEEC): Neumann's double integral M = μ₀/4π·∬ dl·dl′/R, with the inner integral in closed form and each bar's cross-section entering as its geometric mean radius 0.2235·(w + t). A solid plane under the loop is a perfect conductor by images: the mirrored loop, carrying the opposite current, takes away most of the inductance of a flat loop close over it. Against closed forms this gives a bar's self inductance within 0.5 % and a square loop's within 2 %.

The loop's inductance L with the switch node's capacitance C (the device's Coss plus its copper over the neighbouring planes) rings at f = 1/(2π√(L·C)) on every edge, damped by ζ = R/2·√(C/L). The loop's resistance alone gives far less damping than real switch nodes show, so a least damping (ζ = 0.05 by default) stands in for the losses the model leaves out. Each edge passes through H(jω) = ω₀²/(s² + 2ζω₀s + ω₀²), the switch node's response through the loop's L–C tank.

The two edges are not alike (TI, SLPA010). The control switch's turn-on (a buck's high side, a boost's low side) is **hard** while the valley current flows into the inductor: the other switch's body diode is conducting it, and the control switch must take that current over and sweep out the diode's reverse-recovery charge Q{sub}`rr` before the node can move. The diode keeps conducting in reverse until the charge is gone, the current ramping at the edge's di/dt = I/t, then snaps off over the edge, so Q{sub}`rr` = ½·I{sub}`rr`·(I{sub}`rr`/(di/dt) + t) gives the recovery current's peak I{sub}`rr`. The hot loop carries this triangle of current. The node, held by the conducting diode until the snap, answers the snap alone: a current I{sub}`rr` leaving the diode for the node's capacitance, through the tank's impedance jωL·H. That rings the hard edge about I{sub}`rr`·Z{sub}`0` higher. The edge's own damping is the least ringing damping.

The control switch's turn-off is **soft** while the peak current flows into the inductor. The inductor current itself carries the node across, so the edge is no faster than C·V/I, into the other switch's body diode, which turns on and clamps it. The clamp takes the ringing's energy: the soft edge is damped at least the soft-edge damping (ζ = 0.5 by default, one overshoot and settled). A valley current below zero (forced PWM at light load) makes the turn-on soft too: zero-voltage switching. But the controller waits only its dead time (20 ns by default) before turning the next switch on. A current too small to carry the node across in that time (C·V/I longer than the dead time) leaves the switch to finish the edge: it is hard, at the entered edge time and the least ringing damping, with no recovery, since no diode was conducting. The trapezoid's spectrum is a sum of its corners' terms, so each edge's two corners pass through their own H.

The ringing is the switch node's capacitance trading charge with the loop's inductance, so its current flows round the hot loop, through the capacitors that close it. By KCL at the switch node, with the inductor current steady over an edge, a buck's high side carries C·dv/dt more and a boost's rectifier C·dv/dt less, where v is the ringing, the switch node's departure from its ideal trapezoid: I{sub}`ring` = jω·C·(H − 1)·V{sub}`ideal` at each harmonic. Its peak is about V/Z{sub}`0`, with Z{sub}`0` = √(L/C): a few amps for a 12 V switch node ringing at a few hundred MHz. It is part of the pulsed current, so the input capacitors of a buck (the output capacitors of a boost) carry it, and with it the inductive coupling and the board model.

(sg-noise-capacitive)=
## Capacitive coupling

A victim's traces are cut into short segments. Across the middle of each, a line through the board finds the copper on every layer within a window: the switch nodes, the planes and power and ground copper (AC ground), and the victim. That cut is a 2D electrostatic problem: ∇·(ε∇φ) = 0 in the stackup's dielectrics (the solder mask over the outer layers, air beyond), solved with triangles graded fine at the conductors' corners, where the field is singular. Holding the victim at 1 V and everything else at 0 gives its capacitance C′ and its mutual capacitance C{sub}`m`′ to each switch node per mm, from the charge on each; the same cut in vacuum gives C{sub}`0`′ and so its inductance L′ = μ₀ε₀/C{sub}`0`′. Cuts that see the same copper are solved once. Against closed forms the cut gives microstrip and stripline impedance within 2 % (Hammerstad–Jensen, Wheeler) and two wires' mutual capacitance within 1 %.

(sg-noise-inductive)=
## Inductive coupling

Each input and output capacitor closes a current loop: in a buck the input capacitors' loops through the switching device carry the pulsed input current, with edges as fast as the switch's, and the output capacitors' loops through the inductor carry its ripple. Each loop carries its capacitor's share of the current. A ground return with no ground copper under it on the loop's layer is taken through the plane, under the loop, as the return current flows at high frequency.

A victim segment and its return current, in the plane under it, link the loops' flux. The partial mutual inductance from each loop segment to each victim segment is Neumann's integral, as for the hot loop. The plane answers the loops' field with eddy currents, an image of the loop: a thin copper sheet is transparent to a loop ℓ across at low frequency and a mirror at high, reflecting Γ = jα/(1 + jα) of it with α = ω·μ₀·(t/ρ)·ℓ/2 (about 0.3 at 10 MHz for a 4 mm loop over 35 µm of copper). So a victim on the loops' side picks up −jω·I·(M − Γ·M{sub}`image`) along each segment, and one on the far side of the plane (1 − Γ)/cosh((1+j)·t/δ) of what it would link there: very little once the plane mirrors the field and the skin effect stops what is left. The EMF is a series source in the victim's line: an open receiver sees nearly all of it, as V = E·Z{sub}`R`/(Z{sub}`D` + Z{sub}`R`).

Checked against closed forms: two lines over a plane (μ₀/4π·ln(1 + 4h²/s²) per length) within 5 %, far loops as dipoles (−μ₀A₁A₂/4πd³) within 5 %, and a strip's inductance over a plane within 10 % of μ₀ε₀/C₀′ from the field solve (PEEC spreads the current across the strip, the field solve puts it on the surface).

(sg-noise-common)=
## The board model and shared-ground coupling

The converter's input and output rails and their ground are AC mode's 2.5D field model ({ref}`above <sg-ac-model>`), with ports: per phase, the pulsed current between the switching device's high-side and ground pins and the inductor current between the inductor's rail pad and the device's ground; every capacitor on the rails; and, for each victim, its driver's ground pads against its receiver's. The board's port impedance matrix Z is solved at a few frequencies per decade and interpolated onto the harmonics. With the capacitors on their ports (impedance Z{sub}`e`), a source current I{sub}`s` divides among them as I{sub}`E` = −(Z{sub}`EE` + Z{sub}`e`)⁻¹ Z{sub}`Es` I{sub}`s`, through the copper's real resistance and inductance, and the voltage at an observing port is the terminated transfer impedance Z{sub}`os` − Z{sub}`oE`(Z{sub}`EE` + Z{sub}`e`)⁻¹Z{sub}`Es` times the source currents. That gives each capacitor's ripple current (which the inductive coupling then uses), the rails' ripple at the device, and ΔV between a victim's grounds. The AC probes ticked for an aggressor are observing ports too, open between the probe's rail and ground pins. Their terminated transfer impedance times the source currents gives the ripple at the load, through the plane's spreading inductance and the capacitors nearer the load.

Only the transfer impedance's resistive part is taken between a victim's grounds. The inductive part of a ground's potential depends on the path it is measured along: the victim's own loop, its trace over the plane, links that flux, which the inductive coupling already counts. (The 2.5D model would also overstate it where a ground plane faces no rail copper: its current spreads wider than a real return, which stays under its forward path.) What is left is the copper's IR drop, skin effect included, between the two grounds.

The receiver judges the signal against its own ground; the driver drives it from its own. So a ground difference ΔV drives the victim's line through the driver's output resistance, a current ΔV/Z{sub}`D` at the driver: a high-impedance receiver sees nearly all of ΔV. With a single capacitor on each rail the board model's split matches the lumped one at the low harmonics, as it must: there is nowhere else for the current to go.

(sg-noise-scan)=
## Scanning for victims

A scan estimates every signal net with a trace near the aggressor's parts, then solves the worst in full. The estimate's capacitive part uses Maxwell's potential coefficients for two wires a distance d apart at height h over a plane, C{sub}`m`′ = 2πε·p₁₂/(p₁₁² − p₁₂²) with p₁₁ = ln(2h/a), p₁₂ = ½·ln(1 + 4h²/d²) and a = w/4, from each trace segment to the nearest switch-node copper. The edge drives C{sub}`m`·dV/dt into the net through the scan's victim type's resistance R (its driver and receiver in parallel), which also charges the net's own capacitance C{sub}`g` (each segment's 2πε/p₁₁ per length, plus the receiver's): over an edge of t = ΔV/(dV/dt), v = C{sub}`m`·R·dV/dt·(1 − e{sup}`−t/τ`) with τ = R·(C{sub}`m` + C{sub}`g`). A low R gives C{sub}`m`·R·dV/dt; an undriven net the charge divider ΔV·C{sub}`m`/(C{sub}`m` + C{sub}`g`). Its inductive part is the full inductive model, which is cheap. The estimate only ranks the nets (its capacitive part errs high, on the safe side); the results are the full solves.

A scanned net's real driver is not known, so by default it is solved as **undriven** (high impedance: 1 MΩ at each end and 5 pF), the worst case for capacitive coupling: nothing holds the line, so the coupled charge divides between the coupling and the line's own capacitance. It is not the worst case for inductive coupling. An EMF along a floating line divides by where the line's capacitance sits, while a low-impedance driver at the far end puts all of it at the receiver. A net that is a victim already keeps its own type, and the scan's type can be changed in Settings.

(sg-noise-victim)=
## The victim's line

Each segment is a lossy transmission line, Z{sub}`0` = √((R′ + jωL′)/(G′ + jωC′)) and γ = √((R′ + jωL′)(G′ + jωC′)), joined where their ends meet into the victim's whole net. The driver is its output impedance to ground; the receiver its input resistance and capacitance, with any termination. The switch node's charge enters each segment as a current jω·C{sub}`m`′·l·V{sub}`sw`, a loop's flux as an EMF in series with each segment, a ground difference through the driver, and the network is solved at every harmonic, once for each mechanism. For a short line this is the lumped weak-coupling result, V = jω·C{sub}`m`·(Z{sub}`D` ∥ Z{sub}`R`)·V{sub}`sw` (Paul): a strong driver holds the line down, and an open-drain line released high, held only by its pull-up, picks up far more. The receiver's noise over a period is compared with its noise margin, from its logic family's JESD8 levels: min(V{sub}`IL` − V{sub}`OL`, V{sub}`OH` − V{sub}`IH`).

The line is also solved as it really sits: held high at V{sub}`OH`, with V{sub}`IH` below it, and held low at V{sub}`OL`, with V{sub}`IL` above it. Only noise toward the threshold counts in each state, so each state's excursion is the noise's largest step that way, against that state's own margin. A driver may hold the line harder one way than the other: an open drain is held high by its pull-up and low by its switch. The line is then solved once per driver resistance. The verdict takes the larger noise of either state against the smaller margin.

(sg-noise-verdict)=
## From harmonics to a verdict

Every source is periodic at the switching frequency, so the victim's response is too: at each harmonic k·f{sub}`sw` the network gives a complex voltage at the receiver, one per mechanism. The waveform over one period is their inverse Fourier series, sampled at least four times per highest harmonic:

```{container} eq
v(t) = Σ{sub}`k` 2·Re(V{sub}`k`·e{sup}`jωkt`)
```

The phases matter. Capacitive noise follows the switch node's dV/dt and inductive noise the loop's di/dt, so they peak at different moments of an edge and can add or partly cancel. The total is therefore the sum of the mechanisms' complex spectra, turned into one waveform, and its peak is not the sum of the mechanisms' own peaks. Each mechanism's peak is still reported alone, and the largest names the **dominant** mechanism, the one to fix first.

The victim's verdict is its total peak |v| at the receiver over a period against its noise margin: PASS at or below 100 %. The peak is usually a short burst on each switching edge, the edge's own coupling followed by the ringing, with quiet between. A receiver that samples away from the edges may tolerate more, and a clock or an edge-triggered input less, so the margin is yours to set when the logic levels' default does not fit.

The Victim noise plot shows the receiver's waveform per mechanism and in total, with the margin; the Spectrum option shows the same as harmonics, where a peak at the ringing frequency or a line resonance points at its cause. Victims the scan added are marked (scan) in the results, and the report's Scan table ranks every net it estimated, with the ones solved in full marked.

The 3D view shows where along the victim the noise couples in. Its line network is linear and reciprocal: the voltage a unit source at segment i puts at the receiver equals the voltage a unit current injected at the receiver puts at segment i. So one extra solve per harmonic, driven from the receiver, gives the transfer from every segment at once. Each segment's sources (its charge current, its EMF, the driver's ground difference) times that transfer give its contribution to the receiver's spectrum; taken at the instant of the peak, the contributions add up exactly to the peak. A segment that adds to the peak is red, one that takes from it blue.
