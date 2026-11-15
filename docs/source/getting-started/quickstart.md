(quickstart)=
# Quick start

## DC voltage drop in ten minutes

*The most common first run*

1. In KiCad, enable **Preferences → Plugins → Enable KiCad API** (once).
2. Open your board in the PCB editor and click the **KiPI-SI** toolbar button. KiPI-SI reads the board (refilling zones first) and draws it in 3D.
3. In the {ref}`Nets <nets>` list on the left, tick the power and ground nets you want to analyze. KiPI-SI pre-ticks a guess the first time.
4. In the **PI setup** panel on the right, {ref}`VRMs tab <dc-vrms>`: click **Add**, pick the regulator's output net and part, set its voltage. Add its **Ground pins** if you want the ground return solved too.
5. {ref}`Loads tab <dc-loads>`: click **Add** for each part that draws current, pick its supply pins, enter its current and a tolerance (e.g. ±3 %).
6. If a sense resistor, ferrite, fuse or load switch sits between two nets you ticked, add it on the {ref}`Series links tab <dc-links>`.
7. Click **Solve all**. Watch the log at the bottom.
8. Read the {ref}`Loads table <dc-tables>` for PASS/FAIL, and click around the 3D view to probe voltages. Switch the field to **Current density** and tick **Arrows** to find bottlenecks.

The setup is saved next to your board as `<board>.kipi_si-setup.yml` every time you solve, so the next session starts where you left off.

## AC impedance of one rail

*After the DC setup has a VRM on the rail*

1. Switch the mode (start of the toolbar, under **Power Integrity**) to **AC**. The setup panel becomes the **AC setup**; VRMs and series links are shared with DC.
2. Make sure the rail's net, its ground and every net its capacitors connect to are ticked in the Nets list.
3. {ref}`Capacitors tab <ac-caps>`: if {ref}`Auto-fill rail <autofill-caps>` filled the rail, its capacitors have models already; check them. Otherwise click **Models from values** to make one model per capacitor value, then enter each model's **ESL** and **ESR** from the datasheet (and check the capacitance).
4. {ref}`Probes tab <ac-probes>`: click **Add**. KiPI-SI picks the busiest part on the rail that also has ground pins, which is usually the load. Or click **From DC load** and pick a DC load: the probe gets that load's supply and ground pins. Set a target impedance, or open the {ref}`target calculator <ac-calc>`.
5. Under the tabs, choose the **Rail** (by its VRM) and **Ground**, then click **Solve rail**.
6. The **Impedance** tab in the middle shows |Z| against frequency. Click a curve to place a cursor and read the values in the Info box.

## Try it without a board of your own

The repository includes an example: a 4-phase 12 V → 0.9 V, 40 A core rail with decoupling and probes already set up. From a development checkout run

`python -m kipi_si examples/multiphase_buck/multiphase_buck.kipi_si.json.gz`

which opens it in standalone KiPI-SI, or open that file with **Open…** (standalone) or **Open snapshot…** (the plugin).
