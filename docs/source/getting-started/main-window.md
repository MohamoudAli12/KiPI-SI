(window)=
# The main window

```{figure} /images/overview.png
:alt: KiPI-SI main window with nets on the left, the board in 3D and the PI setup on the right

The main window in DC mode.
```

The Board, setup and Log panels are dock widgets: drag their title bars to move them or float them in their own windows. A floating panel has its own minimize and maximize buttons, and **F11** (with the panel clicked) toggles it full screen. Double-click its title bar, or drag it onto the main window, to dock it again.

## Starting KiPI-SI

- **Plugin or standalone.** Started from the KiPI-SI button in KiCad's PCB editor, KiPI-SI runs as the **plugin**: it reads the board open in the editor and can re-read it, refill its zones and select items in it. Started any other way (`python -m kipi_si`, or the `kipi_si` command), it runs **standalone**: it opens board files with **Open…** and needs no KiCad. The title bar then ends in *(standalone)*, and the controls that need KiCad are hidden (see the {ref}`toolbar <toolbar>`). Standalone opens KiCad board files (`.kicad_pcb`), ODB++ jobs, HyperLynx files (`.hyp`) and KiPI-SI snapshots (`.kipi_si.json.gz`).

- **KiCad board files.** A `.kicad_pcb` from KiCad 7 to 10 reads the same as the plugin reads it from KiCad, so a board set up in the plugin opens standalone with its setup. Net classes come from the `.kicad_pro` next to it. KiPI-SI uses the zone fills saved in the file and cannot refill them: **fill the zones in KiCad (B) and save** before opening. Zones saved unfilled are listed under **Placeholders** in the {ref}`board summary <info>`.

- **ODB++.** Open a job as a `.zip`, `.tgz` or `.tar.gz`, or unpacked by picking its `matrix/matrix` file. KiPI-SI reads the copper as the job gives it and the stackup from its layer matrix. The setup is found by the job's name: export `Board.zip` beside `Board.kicad_pcb` to share the board's setup. Export at 6 decimals if your tool asks: KiCad's default of 2 rounds coordinates to 10 µm. What the job leaves out (copper drawings' nets, a dielectric's thickness) is listed under **Placeholders**.

- **HyperLynx.** Open a `.hyp` file (KiCad writes one with *File → Export → Hyperlynx*). KiPI-SI reads its stackup, pad stacks and each net's pins, vias, tracks and copper polygons as the file gives them. The file does not say where a part sits or how it is turned, so each part is placed in the middle of its pads (listed under **Placeholders**); KiCad's export also leaves out pads with no net. The setup is found by the file's name, as for an ODB++ job.

- **Standalone setup.** Start standalone KiPI-SI with its launcher: double-click `kipi_si_launcher.pyw` (Windows) or run `python kipi_si_launcher.py`. The first start installs KiPI-SI's packages into an environment of its own. The setup window lists each package with its size and the totals, and offers PARDISO on Windows and Linux x86-64; nothing is installed until you click **Install**. Later starts open KiPI-SI straight away. To add or remove PARDISO later, use **About → Manage dependencies…**: KiPI-SI closes, the setup opens, and KiPI-SI starts again afterwards.

  ```{figure} /images/launcher_setup.png
  :alt: The launcher's setup window listing packages and the PARDISO option

  The setup window on a first start.
  ```

- **Pin to the taskbar** (Windows): right-click KiPI-SI's taskbar button while it is open, or its Start menu shortcut (`python kipi_si_launcher.py --create-shortcut`), and choose *Pin to taskbar*. The pinned button starts standalone KiPI-SI through the launcher, even when it was pinned from the plugin, since only KiCad can start the plugin; a running KiPI-SI of either kind shows on that button.

- **Task Manager**: KiPI-SI shows as *KiPI-SI* with its icon, not as Python, in Windows Task Manager, macOS Activity Monitor and Linux System Monitor or `top`. On Windows it runs on `KiPI-SI.exe`, a copy of its environment's Python that it makes in the environment's `Scripts` folder the first time, with the Python DLLs it needs beside it. Should that copy not start, KiPI-SI runs on `pythonw.exe` as before and does not try it again until Python or KiPI-SI changes.

- While KiPI-SI starts it shows a **welcome screen** with its version, whether it runs as the plugin or standalone, and the versions of Python and its main packages. It closes on its own, or when you click it.

- **One KiPI-SI at a time** (one plugin and one standalone). Clicking the KiPI-SI button while the plugin is already open brings the open window to the front instead of opening a second one; starting standalone KiPI-SI again does the same for the standalone window. The two never take each other's place. A KiPI-SI that crashed does not block the next one.

- **One KiCad at a time.** KiPI-SI talks to KiCad through its API, which cannot tell two open KiCads apart, so KiPI-SI will not connect (at start or on **Load from KiCad**) while more than one KiCad project manager or PCB editor is open. The message names each one with its process ID. See {ref}`Troubleshooting <ts-multiple-kicad>`.

(typing-values)=
## Typing values

A number on its own is in the field's unit. Fields in an SI unit (Ω, F, H, Hz, A, V, W, m) also take a prefix, with or without the unit, and convert it to the field's unit: in a µF field, `10n`, `10 nF` and `0.01` are all 10 nF. A resistance can be written `2 mOhm`, `2mΩ` or `4k7`. Prefixes are case sensitive (`m` is milli, `M` is mega), and `u` stands for µ. Fields in other units (%, °C, A/µs, µΩ·cm) take plain numbers. A field shows its usual number of decimals, plus more when a small typed value needs them.
