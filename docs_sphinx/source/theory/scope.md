# Uses, limits and further reading

(sg-uses)=
## What PI simulation finds

Design problems KiPI-SI typically exposes, and where to look for each:

```{list-table}
:header-rows: 1
:class: kipi-table

* - Problem
  - How it shows
  - Typical fix
* - Neck-downs
  - A bright spot in the current density where a plane narrows between holes, or a pour squeezes past a connector.
  - Widen the path, move the obstacle, add a parallel layer.
* - Too few vias
  - Vias over their current rating in the via table, or one via carrying most of the current while its neighbors idle.
  - Add vias, spread them along the current's path.
* - Load out of tolerance
  - A load FAILs; the voltage map shows where the drop is.
  - Thicker copper, a wider pour, the VRM closer, or remote sense at the load, or add more parallel copper planes.
* - Ground drop
  - The ground net's own voltage map, with load grounds sitting tens of mV above the VRM.
  - Solid ground under the current's path; no slots across it. More ground planes
* - Sense in the wrong place
  - The sense point meets its set voltage while the far loads fail.
  - Sense at the most critical (high current, tighter tolerance) load, or where the loads are grouped.
* - Hot spots
  - The temperature map, the hottest copper per layer, and a drop that grows with each electro-thermal pass.
  - More copper or layers, a wider path, airflow.
* - Anti-resonance peaks
  - |Z| above the target between two capacitor groups, or where the plane resonates.
  - Add intermediate values, change ESR, physically move capacitors in the layout.
* - Capacitors too far away
  - High impedance above a few MHz at the probe despite enough capacitance on the rail.
  - Move capacitors next to the pins, shorten their vias, use thinner dielectric to ground. Consider smaller case size/lower ESR/lower ESL capacitors at load. Adding these at supply will do little.
* - Victim beside the switch node
  - Capacitive coupling dominant; the victim's results show tens of fF to the switch node over a long run beside it.
  - Move the trace away or onto a layer shielded by a plane, keep the switch-node copper small, slow the edges.
* - Large hot loop
  - Inductive coupling dominant; a hot-loop inductance of several nH and ringing at tens to hundreds of MHz.
  - Put the input capacitors right at the switching device, with a solid ground plane on the next layer; route victims on the far side of that plane.
* - Shared ground return
  - Common-impedance coupling dominant; a victim whose driver and receiver sit on either side of the converter's current.
  - Keep the switching current's return away from the victim's ends; more ground copper or vias between them.
* - Weak victim drivers
  - Open-drain or high-impedance lines FAIL where push-pull lines pass.
  - A stronger pull-up, a series or parallel termination, or a filter at the receiver.
```

(sg-limits)=
## What KiPI-SI does not model

- **DC**: copper is solid and its thickness uniform. Plating variation and etch undercut are not modeled; KiPI-SI uses the stackup's thicknesses.
- **Thermal**: steady state only, with one temperature through the board's thickness and no heat carried away by the parts, enclosure or conduction into the mountin. No heatsinks; this tool is meant to model copper losses and expose weak points, not simulate the thermal scenario of an entire system.
- **AC**: the regulator is left out (open-loop impedance). The package and die are not in the model; probes sit on the board's pads. Capacitors are fixed RLC models, so DC bias and aging are for you to apply to the value you enter. Radiation and coupling to signal nets are not modeled.
- **Coupled Noise**: the converter is ideal switches with set edges, not a transistor-level model, and its hot loop is drawn straight between pads. Coupling is quasi-static (no radiation; long lines are transmission lines, but each cut is 2D). The capacitor loops' current is their capacitor's; the inductor's own field (a shielded inductor's leakage) is not modeled. Shared-ground coupling is through the converter's ground net only, between the victim's two ends.

Like any simulation, the results are only as good as the setup. Check that the load currents are worst case, the capacitor values effective, and the stackup right. The tool is incredibly powerful with thoughtful and complete inputs.

(sg-more)=
## Further reading

- {doc}`KiPI-SI user guide </getting-started/overview>`: setting up and running each analysis, and what every result means.
- L. D. Smith, R. E. Anderson, D. W. Forehand, T. J. Pelc and T. Roy, "Power distribution system design methodology and capacitor selection for modern CMOS technology," *IEEE Transactions on Advanced Packaging*, vol. 22, no. 3, pp. 284–291, Aug. 1999.
- J. R. Shewchuk, "Triangle: Engineering a 2D quality mesh generator and Delaunay triangulator," in *Applied Computational Geometry*, Springer, 1996.
- M. Swaminathan and A. E. Engin, *Power Integrity Modeling and Design for Semiconductors and Systems*, Prentice Hall, 2007.
- E. Bogatin, *Signal and Power Integrity — Simplified*, 3rd ed., Prentice Hall, 2018.
- C. R. Paul, *Analysis of Multiconductor Transmission Lines*, 2nd ed., Wiley-IEEE Press, 2008. Weak-coupling crosstalk between lines (chapter 3).
- C. R. Paul, *Introduction to Electromagnetic Compatibility*, 2nd ed., Wiley, 2006.
- D. A. Hill, K. H. Cavcey and R. T. Johnk, "Crosstalk between microstrip transmission lines," NIST IR 5015, National Institute of Standards and Technology, Dec. 1993 ([PDF](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir5015.pdf)); also *IEEE Transactions on Electromagnetic Compatibility*, vol. 36, no. 4, 1994.
- T. Hubing, "Transmission line crosstalk," LearnEMC course notes, chapter 6 ([PDF](https://learnemc.com/ext/pdf/EMC-Course-Notes/CH06-Transmission-Line-Crosstalk.pdf)). Capacitive and inductive crosstalk with the near- and far-end terminations.
- "Crosstalk reduction between PCB traces," *In Compliance Magazine* ([article](https://incompliancemag.com/crosstalk-reduction-between-pcb-traces/)).
- A. E. Ruehli, "Inductance calculations in a complex integrated circuit environment," *IBM Journal of Research and Development*, vol. 16, no. 5, pp. 470–481, Sept. 1972. Partial inductance, the basis of PEEC.
- A. E. Ruehli, G. Antonini and L. Jiang, *Circuit Oriented Electromagnetic Modeling Using the PEEC Techniques*, Wiley-IEEE Press, 2017.
- C. Hoer and C. Love, "Exact inductance equations for rectangular conductors with applications to more complicated geometries," *Journal of Research of the National Bureau of Standards*, vol. 69C, no. 2, pp. 127–137, 1965.
- G. Zhong and C.-K. Koh, "Exact closed-form formula for partial mutual inductances of rectangular conductors," *IEEE Transactions on Circuits and Systems I*, vol. 50, no. 10, pp. 1349–1352, Oct. 2003.
- "Accurate calculation of partial inductances for the orthogonal PEEC formulation," *IEEE Transactions on Electromagnetic Compatibility*, vol. 63, no. 1, pp. 82–92, Feb. 2021 ([ETH Zurich record](https://www.research-collection.ethz.ch/entities/publication/00342fb5-9ba4-4c68-8594-47f3e5e8826e)). Which closed-form formula to use for which pair of bars.
- J. Lee, M. D. Rotaru, M. K. Iyer, H. Kim and J. Kim, "Analysis and suppression of SSN noise coupling between power/ground plane cavities through cutouts in multilayer packages and PCBs," *IEEE Transactions on Advanced Packaging*, vol. 28, no. 2, pp. 298–309, May 2005. Transfer impedance between plane cavities.
- G. Feng, G. Selli, K. Chand, M. Lai, L. Xue, J. L. Drewniak, B. Archambeault, S. R. Connor and E. Matoglu, "Analysis of noise coupling result from overlapping power areas within power delivery networks," *Proc. IEEE International Symposium on Electromagnetic Compatibility*, Portland, OR, vol. 2, pp. 304–309, Aug. 2006.
- B. Archambeault and J. Drewniak, *PCB Design for Real-World EMI Control*, Kluwer Academic, 2002.
- H. W. Ott, *Electromagnetic Compatibility Engineering*, Wiley, 2009. Switching converter hot loops and switch-node coupling.
- Analog Devices, "The unseen ring: taming parasitics in buck converters using a snubber" ([article](https://www.analog.com/en/resources/technical-articles/the-unseen-ring.html)). Switch-node ringing from the hot loop's inductance and the switch's output capacitance.
- Texas Instruments, LV5144 and LM5149 datasheets, layout sections ([LV5144](https://www.ti.com/document-viewer/LV5144/datasheet/GUID-8D69104D-0FA2-4D33-9512-F21E27F89E74), [LM5149](https://www.ti.com/document-viewer/LM5149/datasheet/GUID-028E4746-6966-49FD-87D4-6B7F91079394)). The power loop's inductance against the MOSFETs' Coss, and how it rings the switch node.
- P. Horowitz and W. Hill, *The Art of Electronics*, 3rd ed., Cambridge University Press, 2015. Outstanding reading for any electronics designer.
