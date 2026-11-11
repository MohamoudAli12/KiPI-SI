(sg-si)=
# Signal Integrity: channels and eyes

Power integrity asks whether the right voltage arrives; signal integrity asks whether the right bits do. At gigabit rates a trace is a transmission line: an edge travels along it at about half the speed of light, reflects wherever its impedance changes, loses its high frequencies to the copper and the dielectric, and picks up its neighbours' edges. The SI mode models a channel the way commercial tools do: field-solved line sections and via models joined into one circuit, its S-parameters, then the eye at the receiver.

(sg-si-xsection)=
## Cross-sections

Each trace is cut into sections about a millimetre long. At each section's middle, KiPI-SI cuts the board at right angles to the trace: the trace, any copper within the window either side (its pair partner, neighbours, plane edges), the planes above and below and every dielectric layer between, solder mask included. A 2D finite element solve of Laplace's equation for each conductor at 1 V gives the capacitance matrix:

```{container} eq
∇·(ε ∇φ) = 0, C{sub}`ij` = charge on conductor i with conductor j at 1 V
```

The same solve with every dielectric replaced by vacuum gives C{sub}`0`, and the inductance follows from it, as the magnetic field does not see the dielectric: L = μ{sub}`0`ε{sub}`0` C{sub}`0`{sup}`−1`. From L and C come each conductor's impedance, a pair's odd, even and differential impedance, the delay and the coupling coefficients. The microstrip and stripline cases agree with Hammerstad-Jensen and Wheeler within about 2 %.

The Quick Scan solves tens of thousands of these cuts, so it trims each one first. A solid plane across the whole cut shields everything beyond it, so only the copper between the trace's nearest planes above and below is kept. The field of a trace over a plane falls off within a few times its height h, so the cut is narrowed to the trace's half-width plus 5h either side (and the pair partner's extent plus 5h for a pair). Cuts are compared with the conductors named by their part (trace, partner, neighbour) rather than their net, ground edges within 0.05 mm taken as equal, and a cut and its mirror image taken as the same. Each distinct cut is solved once, on a mesh twice as coarse. On a 6-layer board of 400 nets this leaves about 40 % of the cuts to solve, and Z0 within about 2 % of the full solve.

(sg-si-loss)=
## Loss: dielectric and copper

Each dielectric layer's permittivity varies with frequency. KiPI-SI uses the Djordjevic-Sarkar wideband Debye model, fitted to its permittivity and loss tangent at the datasheet frequency, so the loss stays causal. The solve records how much of each conductor's field energy lies in each layer, so C(ω), and from its imaginary part the conductance G(ω), follow at every frequency without solving again.

Current crowds into a skin δ = √(ρ/(πfμ)) deep at the copper's surface, following the surface charge. From the vacuum solve's surface charge q on each edge,

```{container} eq
R{sub}`ij` = R{sub}`s` Σ q{sub}`i` q{sub}`j` ds, R{sub}`s` = ρ/δ
```

which is Wheeler's incremental inductance rule. It is within about 3 % of it on microstrips. Rough copper lengthens the current's path: Hammerstad's and Groisse's factors from the RMS roughness, or Huray's from the nodules' size and density, multiply R. At low frequency R tends to the DC resistance, and the two join smoothly.

(sg-si-vias)=
## Vias and the return path

A via is a chain along its barrel: the barrel's inductance between layers, and at each layer the capacitance of its pad or barrel to the planes around it through the antipad, from an axisymmetric field solve. The barrel past the last layer the signal uses is the stub, which resonates near a quarter wavelength. When a signal changes layers between two planes, its return current must change planes too, and it does so through the plane pair. KiPI-SI takes the parallel-plate impedance matrix of every via of the channel crossing that pair together with the ground vias near them. That matrix is the modal sum of the rectangular cavity the board's outline gives the planes: its static part summed on a mode grid fine against the vias' radii and spacing, the frequency-dependent rest added separately. The stitching vias are then shorted (a Schur reduction that cancels the plane capacitance exactly), which leaves the vias' return impedance. Near ground vias, that is an inductance, and it falls as more of them are added. With none, it is the plane pair's capacitance and resonances, which show in the channel's loss. A pair's two vias share the planes, so they are coupled through the same matrix.

(sg-si-network)=
## The channel circuit

Each section is an N-conductor lossy transmission line. Its admittance comes from the modal decomposition of ZY, Y{sub}`11` = Y{sub}`c`·coth(Γl) and Y{sub}`12` = −Y{sub}`c`·csch(Γl). The sections, the via chains, the series parts and the buffers' package R, L and C are stamped into one nodal admittance matrix. At each frequency it is reduced to the ports at the dies, then converted to S-parameters (mixed-mode for pairs). The TDR is the step response of S{sub}`11` (or S{sub}`dd11`) through a Gaussian edge.

(sg-si-eye)=
## Eyes, equalisers and COM

With the interface's source and termination at the ports, the transfer to the receiver's die, through an inverse FFT, gives the response to one bit: the pulse response. Its samples one UI apart are the cursors. Every bit pattern's received level is the sum of the cursors the bits switch on, so the distribution of each level is the convolution of each cursor's two-point distribution. Adding the interface's random jitter (Gaussian), deterministic jitter (dual-Dirac) and noise gives the statistical eye. It is computed on 128 phases a UI (the pulse resampled between its samples). Its contours at the target BER and at 10{sup}`−3`, 10{sup}`−6` and 10{sup}`−9` show how the eye closes as the BER falls. The eye's width is the open run of the target contour, and its height is taken at the middle of that run. The bathtub is the error probability of a bit sampled at the eye's threshold, against phase. The PRBS waveform eye folds the simulated pattern on two UIs, centred half a UI from the mean of its threshold crossings. Each step between samples is drawn as a line, so the traces are continuous.

Equalisers reshape the pulse. The transmitter's FFE taps subtract delayed copies of the bit. The receiver's CTLE (IEEE 802.3's form) boosts the high frequencies the channel lost. Its DFE cancels the first post-cursors. KiPI-SI tries the interface's FFE presets and CTLE gains and keeps the pair with the tallest eye. COM is 20 log{sub}`10` of the main cursor over the residual ISI, crosstalk and noise at the target BER.

(sg-si-transient)=
## Buffers and the transient

IBIS describes a buffer by its pull-up, pull-down and clamp I-V tables and how fast it switches between them (the rising and falling waveforms, or a ramp). From them KiPI-SI derives the two switching coefficients K{sub}`u`(t) and K{sub}`d`(t) at the chosen corner, so that I = K{sub}`u`·I{sub}`pu`(V) + K{sub}`d`·I{sub}`pd`(V) + clamps. The channel's S-parameters become impulse responses. At each time step the waves already travelling are convolved, and Newton's method solves each port's nonlinear buffer against them, as in a SPICE simulator's S-parameter element. Generic buffers are the same with linear tables and a raised-cosine edge.
