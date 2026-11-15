(si-plots)=
# SI plots

The **SI plots** tab shows the channel picked in the panel. **Show** picks:

- **Eye diagram**: the statistical eye's probability (log colour scale), centred on the eye, with its contours at the target BER (solid) and at 10{sup}`−3`, 10{sup}`−6` and 10{sup}`−9` (dashed), the eye height and width as arrows, and the receiver's mask. Under it, the **bathtub** gives the BER of a bit sampled at the threshold against time. **Equalised** shows it after the chosen equaliser (untick for the raw channel). **PRBS waveform** shows the eye of the channel's PRBS pattern instead, its traces drawn as lines, without jitter or noise.
- **Impedance (TDR)**: the impedance seen from the driver along the channel, with the interface's edge; vias and connectors show as dips and bumps.
- **S-parameters**: insertion and return loss (differential for pairs), mode conversion and each aggressor's NEXT and FEXT, with Nyquist and the limits marked.
- **Waveforms at the dies**: the transient with the buffers, at the driver and the receiver.
- **Pulse response**: one bit through the channel, with its cursors one UI apart.
