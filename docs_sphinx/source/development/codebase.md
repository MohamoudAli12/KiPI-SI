# Codebase layout

| Path | Purpose |
|---|---|
| `kipi_si_entry.py`, `plugin.json` | KiCad IPC plugin action (runs KiPI-SI as the plugin) |
| `kipi_si/__main__.py` | `python -m kipi_si` / `kipi_si`: standalone, or the plugin with `KIPI_SI_HOST=plugin` |
| `kipi_si_launcher.py`, `.pyw` | Standalone launcher: sets up KiPI-SI's environment on the first start, then starts KiPI-SI in it |
| `kipi_si/launcher/` | The launcher itself, standard library only: environment, Python discovery, package list, installer and setup screens |
| `kipi_si/host.py` | Plugin or standalone: how KiPI-SI was started |
| `kipi_si/core/` | Shared by every analysis: board model, copper geometry, meshing, sparse solvers, 3D meshes, progress reporting |
| `kipi_si/sources/` | Where boards come from: the running KiCad (IPC), `.kicad_pcb` files, ODB++, HyperLynx and snapshots |
| `kipi_si/dc/` | DC analysis: conduction FEM, power-tree setup and solve, thermal, reports, results views and panel |
| `kipi_si/ac/` | AC analysis: PDN impedance over frequency, field solver and sweep, targets, transient, report and panel |
| `kipi_si/noise/` | Coupled Noise analysis: waveforms, hot loop parasitics, coupling extraction, victim solves, report and panel |
| `kipi_si/si/` | Signal Integrity: 2D cross-section field solver, via models, channel circuit, S-parameters, IBIS, transient, eyes and equalisers, Quick Scan, report and panel |
| `kipi_si/gui/` | PySide6 application shell shared by every mode: main window, mode switch, 3D viewer, worker threads, About and Help |
| `docs/help.html` | The user guide opened by **Help**; a single offline HTML file |
| `docs/solver-guide.html` | The Solver Guide: PI background and how the solvers work |
| `kipi_si/compat.py` | Opens results files saved by earlier versions, from before modules moved |
| `examples/` | Example boards as snapshots with their PI setups, and the scripts that generate them |
