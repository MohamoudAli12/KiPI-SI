(workflows)=
# Step-by-step workflows

(wf-first-dc)=
## 1. A first DC IR-drop check of one rail

1. Tick the rail and its ground in the Nets list; untick everything else.
2. VRMs tab: **Add** a **Source** on the regulator's output pins at the target voltage. Add its ground pins.
3. Loads tab: **Add** each consumer with its current, tolerance and ground pins.
4. **Solve all**. Check the Loads table. For a FAIL, double-click the row, choose **Voltage**, and click around the load's pins to see where the drop comes from.
5. Switch to **Current density** with **Arrows** to find the bottleneck, change the layout in KiCad, and use **Load from KiCad** and **Solve all** again.

(wf-tree)=
## 2. A full power tree (input → switcher → LDO)

1. Tick every rail in the chain and the ground.
2. Add the input as a **Source** (e.g. the 12 V connector).
3. Add the switcher as **Switcher** with its efficiency, output pins (inductor), **Input pins** on the 12 V net, and ground pins.
4. Add the LDO as **LDO** with its quiescent current, dropout and **Input pins** on the switcher's output.
5. Add loads on each rail and solve. The VRMs table shows each converter's input current, which includes everything downstream, and its conversion loss.
6. Set **Input range** and **Dropout** to catch a regulator starved by upstream drop: its loads show {bdg-danger}`VRM OUT OF REGULATION`.

(wf-multiphase)=
## 3. A multi-phase regulator

1. Add the VRM and set phase 1's output pins (its inductor), input pins and ground pins.
2. Set **Phases** to the number of phases. Each new phase takes the next parts in sequence (phase 1 on `L1` and `Q1` gives phase 2 `L2` and `Q2`), or the same parts on the next sheet of a board annotated by sheet (`L101 → L201`), or copies the previous phase when there is no next part.
3. Choose each phase in **Edit phase** to check its pins, and change any that are wrong.
4. Set the shared target voltage, type, efficiency and sense pins once.

Each phase carries an equal share of the output current and settles at whatever voltage its copper needs. The VRM regulates its sense pins or, without them, the average of its phase outputs. The VRMs table lists each phase under its VRM: unequal phase voltages show a layout imbalance.

(wf-sense)=
## 4. Remote sense

1. On the VRM, set **Sense pins** to the point the feedback trace connects to (often the load's supply pins).
2. For differential sensing, also set **Ground sense pins** on the ground net (the VRM needs ground pins too).
3. Solve. The sense point sits exactly at the regulated voltage; pins nearer the VRM read *above* it (a boost). The tolerance check catches both directions.
4. To hold several points at the regulated voltage at once (mesh remote sense), tick **Mesh sense**, set **Sense points** and pick each point's pins in turn with **Edit sense point**. Every point is then a fixed voltage, the VRM's current entering there.

(wf-partial)=
## 5. Solving only part of the board

When some rails are not routed or modeled yet, open the **Solve** tab and untick their groups. The rest solves, with the substitutions described under {ref}`Solve tab <dc-solve-tab>`. Untick the group a **Cannot solve** message names to get past a setup problem while you fix it.

(wf-thermal)=
## 6. Thermal and current capacity checks

1. Thermal tab: tick **Electro-thermal co-simulation**, set ambient and airflow, and limits for maximum temperature and rise.
2. On the Vias results tab, set the **Current limit** per via from your fab's via current rating (it starts at 1 A).
3. **Solve all (electro-thermal)**. Read the Thermal tab for the hottest point per layer, and sort the Vias tab by current for overloaded vias.
4. Use the **Temperature** field to see the map; double-click a Thermal row to jump to its group.

(wf-decoupling)=
## 7. Designing decoupling to a target impedance (AC)

1. Make sure the rail has a VRM (Source is fine), and tick the rail, its ground and any nets joined by series links.
2. Switch to **AC**. Capacitors tab: **Models from values**, then enter ESL and ESR for each model from the datasheets.
3. Probes tab: add a probe on the device's power and ground pins. Use the calculator for the target, or a custom mask from the device vendor.
4. **Solve rail**. In the plot, put the cursor on the worst peak (the table's **Worst |Z|** tells you where).
5. Change capacitor models (values, counts by re-assigning parts) or the layout, and solve again. Each probe's margin in dB shows the improvement.
6. To compare rails, solve each and switch between them with **Rail**; each keeps its last result for the session.

Capacitors listed under "have no model and were left out" are not part of the result: give them a model or confirm they really do not belong on this rail.

(wf-offline)=
## 8. Sharing a board and its results

- **Save snapshot…** stores the board; anyone with KiPI-SI can open it with **Open snapshot…**, or with **Open…** in standalone KiPI-SI, without KiCad or your design files.
- Keep `<board>.kipi_si-setup.yml` in version control next to the board.
- Click **Report** with **HTML** chosen for a single file you can email: it needs nothing but a browser.
- **Export ▾ → Save results…** (DC) or **Save results…** (AC) lets you reopen a long solve later with **Open results…**.
