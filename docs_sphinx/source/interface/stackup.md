(stackup)=
# Stackup window

The **Stackup** toolbar button opens a window with the board's layers top to bottom: each copper layer and each dielectric with its thickness, each dielectric's material, εr and in-plane thermal conductivity, and each copper layer's conductor and resistivity. Every analysis, DC and AC, uses this stackup, and the 3D view draws it. The window can stay open beside the main window.

Beside the table, a cross-section draws the layers to scale, top to bottom: copper in its layer colour, each dielectric in a colour for its material, and each layer's thickness beside it in the unit chosen. It follows the thicknesses as you type them. A layer too thin to see at the window's size, such as a copper foil on a thick board, is drawn 3 pixels tall, and its label gives the real thickness; where the labels do not all fit, only the copper layers are labelled and the rest show on hover. Click a layer in the drawing to edit its thickness in the table.

The solder mask and silkscreen on each side are listed above and below the copper, in their color. They come from the board: KiCad's stackup gives the mask's thickness and color, an ODB++ job its mask and silkscreen layers. KiCad gives a silkscreen no thickness, so KiPI-SI takes 15 µm; a board with no stackup of its own gets KiCad's default, a 10 µm mask and a silkscreen on both sides. Unlocked, their thicknesses can be changed. They sit outside the board, so they do not add to its thickness or move any layer. Only the electro-thermal solve uses them: heat leaving the outer copper for the air crosses them (see {ref}`Thermal <dc-thermal>`).

```{figure} /images/stackup.png
:alt: The Stackup window listing copper and dielectric layers

The Stackup window.
```

## Controls

```{list-table}
:header-rows: 1
:class: kipi-table

* - Control
  - What it does
* - **Lock to imported values**
  - Ticked (the default), the thicknesses, materials and εr are the ones read from KiCad's board stackup. Untick it to try others: type a new thickness for any copper or dielectric layer, or choose a dielectric's material or type its εr. The layers above and below move with a thickness change, and the total board thickness shows under the table next to KiCad's. Ticking it again goes back to KiCad's values.
* - **Thickness unit**
  - Shows and takes the thicknesses in µm, mm, mil or oz (1 oz = 35 µm). Ounces are a copper weight, so in oz the dielectrics show in mil. In a µm or mm field a value can also carry its own unit, like `35um` or `0.2mm`. KiPI-SI remembers the unit.
* - **Material** (dielectrics)
  - Each dielectric's material, from the list KiPI-SI knows: FR4 core and prepreg, polyimide, Kapton, Rogers RO4350B, RO4003C, RO3003 and RT/duroid, PTFE, polyolefin, alumina and aluminum nitride ceramics, and an aluminum metal core. KiCad's own name for the material is listed too when it is not one of these. Choosing a material sets its typical εr (a datasheet value near 1 GHz; type another if your laminate's differs) and its in-plane thermal conductivity **k**, which the electro-thermal solve uses. Type over k, unlocked, if your laminate's differs; choosing a material again goes back to its typical value. The solve also needs the conductivity through the laminate, from one copper layer to the next: KiPI-SI takes the material's typical through-plane value (FR4 core 0.3 W/m·K), and a k you type keeps the material's ratio of the two. A ⚠ beside k means KiPI-SI did not recognize KiCad's name and took the layer as FR4. Setups from before 0.8.0 with a Thermal tab **Laminate k** open with that value as every dielectric's k.
* - **Material** (copper layers)
  - What each copper layer is made of. *Copper (board Resistivity)* uses the **Resistivity** and **TCR** below. Or choose annealed copper, electrodeposited or rolled-annealed copper foil (IPC-4562's maximum resistivity), silver, gold, aluminum, nickel or tin: this sets the layer's resistivity, its TCR for the electro-thermal solve, and its thermal conductivity **k** for heat spreading. A resistivity typed in the table afterwards wins; setting it back to `default` returns the layer to the board's copper. A layer given a resistivity by hand in an earlier version shows as *Custom resistivity*. Like the thicknesses, a layer's conductor is changed only with **Lock to imported values** unticked; ticking it again keeps the conductor chosen.
* - **εr**
  - Each dielectric's constant, for the AC solve. `default` means the stackup gives none (or the material is a metal), and the **Default εr** below applies. Every other dielectric uses the εr from KiCad's board stackup (Board Setup → Physical Stackup); a dielectric made of several sublayers gets their series combination. The AC log and report list the εr used for each dielectric.
* - **Resistivity at 20 °C** (table)
  - A copper layer's own resistivity, set by its conductor or typed in while unlocked; `default` uses the **Resistivity** below.
* - **Resistivity**, **TCR**
  - Resistivity at 20 °C (annealed copper, 1.724 µΩ·cm, by default) of every layer left at the board's copper and of via plating, and its temperature coefficient (0.00393 /°C for copper), used by the electro-thermal solve. These are setup settings, so they can be changed while the stackup is locked.
* - **Loss tangent**, **Default εr**
  - For the AC solve: the dielectric loss (FR4 about 0.02), which damps the plane resonances, and the dielectric constant of every dielectric whose εr is `default`. Setup settings too, so they can be changed while the stackup is locked. (Before 0.9.0 they were on the AC setup's Mesh tab.)
* - **Reset**
  - Back to KiCad's thicknesses, materials and εr, still unlocked.
```

- The stackup and resistivities are saved with the PI setup. An edited stackup is used again the next time the board is opened (unlocked). If a layer has been added, removed or renamed in KiCad since, the log says so and KiCad's stackup is used.
- To compare stackups, solve, edit, and solve again. A stackup change clears the DC results, which were for the old stackup; the AC results stay until a rail is solved again. Reports note a stackup edited in KiPI-SI.
- KiCad's API cannot change a board's stackup yet, so edits stay in KiPI-SI. To keep a stackup you settle on, enter it in KiCad's *Board Setup → Board Stackup → Physical Stackup*.
- A board snapshot (**Save snapshot**) keeps KiCad's stackup; the edits live in the setup.
