(si-primer)=
# Reading SI results: what good and bad look like

A plain-language guide to every Signal Integrity result KiPI-SI shows: what it means, how to read it, and what a good and a bad channel look like. The plots are KiPI-SI's own, from the example board `examples/si_demo`, which has a deliberately good and a deliberately bad version of each kind of channel.

:::{tip}
**The short version.** A signal is good when it reaches the receiver tall enough (eye height), at the right time (eye width), and without ringing. It loses height to **loss** (the trace soaks up energy), to **reflections** (impedance changes bounce part of it back) and to **crosstalk** (neighbours leak into it). Every plot below shows one of these three, from a different angle.
:::

(si-basics)=
## The basics in six ideas

1. **A fast signal is a wave, not a voltage.** When an edge rises in less time than it takes to travel the trace, the trace stops acting like a wire and behaves as a *transmission line*. On FR-4 a signal travels about 15 cm per nanosecond, so a 100 ps edge is only 1.5 cm long: almost every trace on a modern board is a transmission line for it.
2. **Impedance is what the wave "feels".** A trace's **characteristic impedance** (Z0, or Zdiff for a pair) is set by its width, its height above the reference plane and the dielectric. Typical targets: 50 Ω single-ended; 85 Ω (PCIe), 90 Ω (USB) or 100 Ω (Ethernet, LVDS, HDMI) differential.
3. **Every impedance change reflects part of the wave.** The reflected share is (Z₂ − Z₁)/(Z₂ + Z₁): a 10 % change reflects about 5 % of the signal back. Vias, pads, connectors, a trace that narrows, or a gap in the plane underneath all change the impedance. The reflection travels back, bounces again, and lands on later bits.
4. **Traces lose energy, more at high frequency.** Copper resistance (worse at high frequency because of skin effect and surface roughness) and the dielectric both absorb energy. Losing high frequencies rounds the edges, so each bit smears into the next.
5. **Neighbours couple.** Two traces side by side share electric and magnetic fields, so a switching neighbour (the *aggressor*) induces noise on the trace you care about (the *victim*). It grows as they get closer and the parallel run gets longer.
6. **A differential pair carries the signal as a difference.** P and N swing in opposite directions and the receiver reads P − N. Noise that hits both equally (common mode) cancels. That only works if the two legs are matched: same length, same impedance, same surroundings.

```{list-table}
:header-rows: 1
:class: kipi-table

* - Term
  - What it means
  - Example
* - Bit rate, UI
  - Bits per second, and the **unit interval**: the time of one bit (1 / bit rate). Eye widths and skew are measured in UI.
  - PCIe Gen 3: 8 Gb/s, UI = 125 ps
* - Nyquist frequency
  - Half the bit rate: the frequency of a 1010… pattern, and where loss is usually judged.
  - 8 Gb/s → 4 GHz
* - Rise time
  - How long an edge takes from 20 % to 80 % (or 10–90 %). Faster edges carry higher frequencies and see more reflections.
  - 40 ps (PCIe), 300 ps (USB 2)
* - dB
  - A log ratio. For signal voltages: −6 dB is half, −20 dB is a tenth, −40 dB is a hundredth. Closer to 0 dB means more of the signal.
  - −3 dB ≈ 71 % of the voltage gets through
* - BER
  - Bit error ratio: the share of bits read wrongly.
  - 10{sup}`−12`: one error in a million million bits
```

(si-tdr)=
## Impedance (TDR)

**What it is.** TDR (time-domain reflectometry) sends a fast edge into the channel and watches what comes back. Each reflection is turned into the impedance at that point, so the plot is an **impedance map along the route**. The x axis is time, and time is distance: a feature at 200 ps is about 1.5 cm in (200 ps is the round trip, there and back).

**How to read it.** Flat inside the green band (the target ±10 %) is good. Up means too much impedance (too little capacitance: a narrow trace, a gap in the plane, a missing return via), down means too little (too much capacitance: a wide pad, a via barrel, a connector). A short blip is a short feature; a long shelf is a long stretch of wrong trace.

```{figure} /images/si_tdr_shapes.png
:alt: Four sketches of TDR shapes: a flat line, a dip, a bump, and open, short and terminated ends

Illustration: the shapes to look for.
```

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item}
```{figure} /images/si_tdr_good.png
:alt: A TDR that stays near 87 ohms inside the target band

{bdg-success}`Good`: PCIe TX0 sits at 87 Ω, inside 85 Ω ± 10 %, for most of its length. The short bump at the start and the dip near 720 ps are local features (the driver's end and a discontinuity near the receiver); the level after 800 ps is the receiver's termination.
```
:::

:::{grid-item}
```{figure} /images/si_tdr_bad.png
:alt: A TDR that runs at 110 to 140 ohms, far above the target band

{bdg-danger}`Bad`: PCIe TX1 runs at 110–120 Ω the whole way, above the band, with a 140 Ω spike at the start and dips at its discontinuities. KiPI-SI flags it: *Zdiff 110–167 Ω, off over 49.8 of 60.6 mm*.
```
:::

::::

```{list-table}
:header-rows: 1
:class: kipi-table

* -  
  - Good
  - Borderline (WARN)
  - Bad (FAIL)
* - Impedance check
  - Every section within the target ±10 %
  - Off target over less than 10 % of the route
  - Off target over 10 % of the route or more
```

**Usual fixes.** Off over the whole route: the trace width or pair spacing is wrong for the stackup (KiPI-SI's Quick Scan suggests a width). A bump in one place: look there for a gap in the plane, a layer change with no return via, or a neck-down. A dip: a large pad, a via or a connector; shrink the pad or add an anti-pad.

(si-sparams-primer)=
## S-parameters: insertion loss, return loss, mode conversion

**What they are.** S-parameters describe the channel frequency by frequency: of a sine wave sent in, how much gets through, how much comes back, and how much leaks elsewhere. They are the frequency view of the same channel the TDR shows in time.

- **Insertion loss** (Sdd21, or S21 single-ended): how much gets through. It starts at 0 dB and falls with frequency. A smooth gentle slope is normal; what matters is the value at **Nyquist** (the dotted line) against the interface's limit (the triangle). Dips and ripples in it mean reflections or resonances.
- **Return loss** (Sdd11, or S11): how much comes back. **Lower is better**: −20 dB means only 10 % of the voltage reflects. The dotted line is the limit up to Nyquist.
- **Mode conversion** (Scd21, pairs only): how much of the differential signal turns into common-mode noise because P and N are not matched. Lower is better.

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item}
```{figure} /images/si_sparams_good.png
:alt: Smooth insertion loss reaching about -6 dB at 16 GHz, mode conversion below -65 dB

{bdg-success}`Good` loss, smooth: the good PCIe pair at 32 Gb/s loses 6 dB at its 16 GHz Nyquist, and its mode conversion stays below −65 dB.
```
:::

:::{grid-item}
```{figure} /images/si_sparams_bad.png
:alt: Rippling insertion loss reaching -15 dB at 16 GHz with deep notches; mode conversion near -20 dB

{bdg-danger}`Bad`: the bad pair loses 15 dB at the same frequency, with notches (resonances from its reflections), and mode conversion up at −20 dB from its unmatched legs.
```
:::

::::

```{list-table}
:header-rows: 1
:class: kipi-table

* - Check
  - Good (PASS)
  - Borderline (WARN)
  - Bad (FAIL)
* - Insertion loss at Nyquist
  - Above the interface's limit (less negative)
  - Up to 3 dB beyond it
  - More than 3 dB beyond it
* - Return loss up to Nyquist
  - Below the limit everywhere
  - Up to 3 dB above it
  - More than 3 dB above it
* - Mode conversion up to Nyquist
  - Below −25 dB
  - −25 to −15 dB
  - Above −15 dB
```

**Usual fixes.** Too much loss: shorten the route, use a lower-loss laminate or smoother copper, or widen the traces (at the same impedance). Poor return loss: fix the impedance changes the TDR shows. Mode conversion: match P and N (length, vias, symmetric breakouts).

(si-xtalk-primer)=
## Crosstalk (NEXT and FEXT)

**What it is.** The share of an aggressor's signal that appears on the victim, in dB. **NEXT** (near-end) is measured at the victim's driver end, **FEXT** (far-end) at its receiver end. Add the neighbouring nets as **Aggressors** in a channel to see it. **More negative is better**: −40 dB is 1 % of the aggressor's swing; −20 dB is 10 %.

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item}
```{figure} /images/si_xtalk_good.png
:alt: Near-end crosstalk around -40 dB

{bdg-success}`Good`: DQ1, spaced three trace widths from its neighbours (the "3W rule"), has NEXT near −40 dB.
```
:::

:::{grid-item}
```{figure} /images/si_xtalk_bad.png
:alt: Near-end crosstalk around -18 dB

{bdg-danger}`Bad`: DQ5, tight against DQ4 and DQ6, picks up −18 dB: over 10 % of each neighbour's swing.
```
:::

::::

```{list-table}
:header-rows: 1
:class: kipi-table

* - Check
  - Good (PASS)
  - Borderline (WARN)
  - Bad (FAIL)
* - Worst NEXT or FEXT up to Nyquist
  - Below −30 dB
  - −30 to −20 dB
  - Above −20 dB
```

**Usual fixes.** Space traces further apart (three widths, or more for fast signals), shorten the parallel run, route on an inner layer (stripline has far less FEXT), or put a ground trace or a reference plane between them.

(si-pulse-primer)=
## Pulse response and ISI

**What it is.** One lone "1" bit sent through the channel, as it arrives. An ideal channel would return a single tall bump one UI wide. A real one spreads it out: the bump shrinks (loss) and leaves a tail (loss and reflections). The orange dots, the **cursors**, are one UI apart: the tallest is the main cursor, the others are how much this bit lands on its neighbours. That leftover on other bits is **intersymbol interference (ISI)**, the main reason eyes close.

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item}
```{figure} /images/si_pulse_good.png
:alt: A tall pulse that settles to zero within two UI

{bdg-success}`Good`: a 590 mV peak, and the tail is gone within about two UI.
```
:::

:::{grid-item}
```{figure} /images/si_pulse_bad.png
:alt: A shorter pulse with a long ringing tail of reflections

{bdg-danger}`Bad`: a lower 460 mV peak, and the tail rings for 15 UI and more with the reflections, dipping −50 mV at 19 UI: those land on later bits.
```
:::

::::

**What good looks like.** A tall main cursor and post-cursors that fall fast and smooth. A long tail that equalisation can learn (a smooth decay from loss) is fine; bumps and dips far out (reflections) are hard to equalise.

(si-eye-primer)=
## The eye diagram

**What it is.** Take the received waveform, cut it into two-UI slices and lay every slice on top of the others. Where the ones and zeros never go, a hole opens: the **eye**. The receiver samples in the middle of it, so the bigger the hole, the more room for noise and timing error.

- **Eye height** (the vertical arrow): how far apart a one and a zero stay at the best sampling time. Noise smaller than this cannot flip a bit.
- **Eye width** (the horizontal arrow): for how much of the UI the eye stays open. Jitter smaller than this cannot make the receiver sample the wrong bit.
- **Contours**: KiPI-SI's eye is *statistical*. The colours are how likely the signal is to be at each point (yellow often, dark rarely). The solid line is where the chance of an error reaches the target BER (usually 10{sup}`−12`); the dashed ones are 10{sup}`−3`, 10{sup}`−6` and 10{sup}`−9`. Height and width are measured on the solid line.
- **The mask** (the green shape): the smallest eye the receiver's datasheet accepts. The eye must contain it.

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item}
```{figure} /images/si_eye_good.png
:alt: A wide open eye, 827 mV by 0.90 UI

{bdg-success}`Good`: PCIe TX0 at 8 Gb/s, open 827 mV × 0.90 UI: thin traces, a clean diamond hole, sharp edges to the colour.
```
:::

:::{grid-item}
```{figure} /images/si_eye_marginal.png
:alt: A nearly closed eye, 97 mV by 0.38 UI, with many traces crossing

{bdg-warning}`Marginal`: the same pair pushed to 32 Gb/s without equalisation. The traces fan out into many levels (ISI) and the hole shrinks to 97 mV × 0.38 UI.
```
:::

:::{grid-item}
```{figure} /images/si_eye_closed.png
:alt: A fully closed eye with no opening at the target BER

{bdg-danger}`Closed`: the bad pair at 32 Gb/s, even with the best equaliser. No hole reaches 10{sup}`−12`; only a small region at 10{sup}`−6` is left. This link would not work.
```
:::

:::{grid-item}
```{figure} /images/si_eye_equalised.png
:alt: The marginal eye reopened by equalisation to 366 mV by 0.88 UI

{bdg-success}`Rescued by equalisation`: the marginal eye above, after the best equaliser KiPI-SI found (here using 3 DFE taps): 366 mV × 0.88 UI.
```
:::

::::

```{list-table}
:header-rows: 1
:class: kipi-table

* - Check
  - Good (PASS)
  - Borderline (WARN)
  - Bad (FAIL)
* - Eye against the mask
  - Height and width both at least the mask's
  - Both at least 70 % of the mask's
  - Smaller still, or closed
```

**Reading the shape.** Thick, fuzzy crossings mean jitter. Several separate rails at the top and bottom mean ISI (each rail is a different bit pattern). Overshoot above the top rail means reflections. A lopsided eye means asymmetric rise and fall, or skew in a pair.

(si-ber-primer)=
## BER and the bathtub curves

**What BER is.** The fraction of bits the receiver gets wrong. Links are specified at 10{sup}`−12` (PCIe, USB) or lower: at 10 Gb/s that is about one error every 100 seconds, which the link's error recovery can absorb. A link at 10{sup}`−6` would make ten thousand errors a second.

**The bathtub curves** show BER against where the receiver samples, so you can see the margin, not just pass or fail:

- **Timing bathtub** (under the eye): BER against sampling time. Near the crossings it is 0.5 (a coin toss); it falls into a valley in the middle. Where the curve crosses the target line (the dotted green 10{sup}`−12`) are the eye's edges, so the gap between the walls at that line is the eye width.
- **Voltage bathtub** (beside the eye): BER against the decision threshold, at the best sampling time. The gap between its walls at 10{sup}`−12` is the eye height.

**What good looks like.** Steep walls and a wide, deep floor: the curve plunges below 10{sup}`−12` and stays there over most of the UI (see the good eye above: the floor spans about 0.8 UI). **Bad**: the walls meet, or the floor never gets down to the line (the closed eye above: the bathtub stays at 1).

(si-eq-primer)=
## Equalisation

Fast receivers and transmitters undo part of the channel's loss themselves. KiPI-SI searches the interface's equalisers for the setting that opens the eye most:

- **FFE** (feed-forward equalisation, at the transmitter): pre-shoot and de-emphasis. It boosts each edge relative to long runs of the same bit, pre-compensating the loss.
- **CTLE** (continuous-time linear equaliser, at the receiver): a filter that boosts high frequencies back up. It also boosts noise.
- **DFE** (decision-feedback equaliser, at the receiver): subtracts the known tail of the bits already received (the post-cursors) from the current one. It cancels ISI without boosting noise, but only for a few UI.

**What it can and cannot fix.** Smooth loss equalises well: the good pair at 32 Gb/s went from 97 mV to 366 mV. Reflections and resonances do not: they land many UI later and change with the pattern, so the bad pair stayed closed. Untick **Equalised** in SI plots to see the raw channel.

(si-com-primer)=
## COM (channel operating margin)

One number for the whole link: the main cursor's signal over all the noise and interference at the target BER, in dB. It folds loss, ISI, crosstalk, jitter and noise together. The idea comes from the IEEE 802.3 Ethernet standards; KiPI-SI's is a simplified form of it.

```{list-table}
:header-rows: 1
:class: kipi-table

* - COM
  - Meaning
* - {bdg-success}`3 dB or more`
  - Passes with margin. The good PCIe pair has 21 dB at 8 Gb/s and 8.5 dB at 32 Gb/s with equalisation.
* - {bdg-warning}`0 to 3 dB`
  - Works on paper, little margin for manufacturing spread or temperature.
* - {bdg-danger}`Below 0 dB`
  - Fails: the noise outweighs the signal. The bad pair at 32 Gb/s: −2 dB.
```

(si-skew-primer)=
## Pair skew

The difference in arrival time between P and N. Skew turns part of the differential signal into common-mode noise (see mode conversion) and slows the differential edge. KiPI-SI gives it as a share of the UI, since what matters is how it compares to one bit.

```{list-table}
:header-rows: 1
:class: kipi-table

* - Check
  - Good (PASS)
  - Borderline (WARN)
  - Bad (FAIL)
* - P/N skew
  - Under 5 % of a UI
  - 5 to 15 %
  - 15 % or more
```

**Usual fixes.** Add a small serpentine on the shorter leg, close to where the mismatch is (at the bend or via that causes it), not at the far end.

(si-waves-primer)=
## Waveforms: overshoot, ringing, ringback

**What it is.** The actual voltage at the driver and the receiver, from a transient simulation with the buffers (IBIS or generic). This is what an oscilloscope probe would show. It matters most for slower single-ended signals (clocks, resets, buses) where there is no eye spec but a false edge would be a fault.

- **Overshoot**: the signal rising past its final level. Too much stresses the receiver's input protection.
- **Ringing**: oscillation after an edge, from reflections bouncing between the two ends of an unterminated line.
- **Ringback**: ringing that swings back toward the logic threshold. If it crosses it, the receiver sees an extra edge: a clock counts twice.
- **Monotonic**: the edge keeps going the same way through the threshold band, never stepping back.

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item}
```{figure} /images/si_waves_good.png
:alt: Clean square edges with no overshoot

{bdg-success}`Good`: CLK\_GOOD has a 33 Ω series resistor at its driver (source termination), so its edges arrive clean and flat.
```
:::

:::{grid-item}
```{figure} /images/si_waves_bad.png
:alt: Edges overshooting to 3.8 V and ringing below 0 V

{bdg-warning}`Overshoot`: CLK\_BAD, the same clock without the resistor, overshoots by 534 mV (16 % of the swing) and rings below 0 V on every edge.
```
:::

::::

```{list-table}
:header-rows: 1
:class: kipi-table

* - Check
  - Good (PASS)
  - Borderline (WARN)
  - Bad (FAIL)
* - Overshoot
  - Under 10 % of the swing
  - 10 to 20 %
  - 20 % or more
* - Ringback
  - Stays more than 5 % of the swing clear of the thresholds
  - Clears them by less
  - Crosses into the threshold band
* - Monotonic
  - Every edge
  - An edge reverses inside the threshold band
  -  
```

**Usual fixes.** Terminate the line: a series resistor at the driver (about the trace's Z0 minus the driver's own output impedance, often 22–33 Ω), or a resistor at the receiver end. Shorter traces and slower edges help too.

(si-cheatsheet)=
## Cheat sheet: every check at a glance

```{list-table}
:header-rows: 1
:class: kipi-table

* - Check
  - Shown in
  - Good
  - Bad
  - Most common cause
* - Impedance
  - TDR
  - Flat inside target ±10 %
  - Off target over ≥ 10 % of the route
  - Wrong width or spacing for the stackup; plane gaps
* - Insertion loss
  - S-parameters
  - Smooth, within the limit at Nyquist
  - > 3 dB past the limit, notches
  - Long route, lossy laminate, stubs
* - Return loss
  - S-parameters
  - Below the limit
  - > 3 dB above it
  - Impedance changes (vias, pads, connectors)
* - Mode conversion
  - S-parameters
  - \< −25 dB
  - > −15 dB
  - Unmatched P and N
* - Crosstalk
  - S-parameters
  - \< −30 dB
  - > −20 dB
  - Traces too close, long parallel runs
* - Skew
  - Results
  - \< 5 % UI
  - ≥ 15 % UI
  - Length mismatch in a pair
* - Eye
  - Eye diagram
  - Contains the mask
  - Under 70 % of the mask, or closed
  - Any of the above, added up
* - COM
  - Results
  - ≥ 3 dB
  - \< 0 dB
  - Any of the above, added up
* - Overshoot
  - Waveforms
  - \< 10 % of swing
  - ≥ 20 %
  - No termination
```

:::{note}
**Where to start.** Fix in this order: the impedance (TDR) first, because reflections are the hardest to equalise; then crosstalk; then loss. Check the eye last, as the sum of everything. The Quick Scan finds most impedance and crosstalk faults across the whole board before you set up any channel.
:::
