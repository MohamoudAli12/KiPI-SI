(noise-solving)=
# Solving an aggressor

## Aggressor and Solve

Below the tabs, pick the **Aggressor** and click **Solve**; problems that stop it are listed in red above. Only one aggressor is solved at a time, and each keeps its last result. **Victims** picks which victims a solve covers: all of them, one by name (quicker while you work on one route), or none (the aggressor's waveforms only).

Tick **Scan nearby nets** to also look for victims you have not named: every signal net with a trace within the scan radius of the aggressor's parts gets a quick estimate of its noise (capacitive from its distance to the switch-node copper, inductive from the full model), and the worst are solved in full as the scan's victim type, undriven by default, and its logic level (Settings). They are marked **(scan)** in the results table. The **Scan radius** slider under it sets how far from the aggressor's parts the scan looks, from 0.5 mm to 500 mm, and shows how many signal nets are inside; it is the same value as Scan radius in Settings. Scan and a chosen victim work together: name the nets you know, scan for the ones you do not.

Click **Report** to write `<board>_<aggressor>_noise_report_<date>_<time>.html` (or `.pdf`) of the shown aggressor's results in the `kipi_si_reports` folder next to the board: the victims against their margins, the aggressor's parasitics, its waveforms, each victim's noise by mechanism, the scan's estimates and the notes. **Open report** opens it again. **Save results…** writes every solved aggressor to a `.kipi_si-noise-results` file that **Open results…** reopens in this mode.
