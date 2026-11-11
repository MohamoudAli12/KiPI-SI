---
html_theme.sidebar_secondary.remove: true
---

# KiPI-SI documentation

```{image} ../../resources/kipi_si_logo_name.svg
:alt: KiPI-SI — Power & Signal Integrity
:height: 110px
:align: center
```

**KiPI-SI** is a power and signal integrity analyzer for printed circuit boards. It runs as a
KiCad 9/10 plugin or standalone on board files (KiCad, ODB++, HyperLynx), and has four
analysis modes: **DC voltage drop**, **AC PDN impedance**, **Coupled Noise** from switching
regulators, and **Signal Integrity** for nets and high-speed channels.

:::{admonition} Status
:class: note
Version {{ release }} is an **alpha** in active development. Treat results as an
engineering estimate and sanity-check anything surprising.
:::

## Where to start

::::{grid} 1 2 2 3
:gutter: 3

:::{grid-item-card} {octicon}`download` Install
:link: getting-started/installation
:link-type: doc

Set KiPI-SI up as a KiCad plugin or as a standalone app.
:::

:::{grid-item-card} {octicon}`rocket` Quick start
:link: getting-started/quickstart
:link-type: doc

Your first DC voltage-drop and AC impedance run in ten minutes.
:::

:::{grid-item-card} {octicon}`book` Walkthrough
:link: getting-started/walkthrough
:link-type: doc

Every step from opening a board to reading the results, mode by mode.
:::

:::{grid-item-card} {octicon}`browser` User interface
:link: interface/index
:link-type: doc

The toolbar, panels, 3D view and keyboard shortcuts.
:::

:::{grid-item-card} {octicon}`checklist` Workflows
:link: workflows
:link-type: doc

Step-by-step recipes for common analyses.
:::

:::{grid-item-card} {octicon}`mortar-board` Theory
:link: theory/index
:link-type: doc

What power integrity is and how KiPI-SI's solvers work.
:::
::::

## Analysis modes

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} DC — Voltage drop
:link: dc/index
:link-type: doc
:img-top: images/current_density.png

IR drop, current density, via currents, copper losses and board temperature, with PASS/FAIL
per load, VRM and via.
:::

:::{grid-item-card} AC — PDN impedance
:link: ac/index
:link-type: doc
:img-top: images/ac_impedance.png

Impedance of the power distribution network over frequency against a flat or custom target.
:::

:::{grid-item-card} Coupled Noise
:link: noise/index
:link-type: doc
:img-top: images/noise_coupling_3d.png

How much a buck or boost converter's switching noise couples onto nearby signal nets.
:::

:::{grid-item-card} SI — Signal integrity
:link: si/index
:link-type: doc
:img-top: images/si_eye_good.png

Quick Scan of every signal net; S-parameters, TDR, eyes, COM and waveforms for a channel.
:::
::::

## Getting help

- Every control in KiPI-SI has a tooltip; press {kbd}`F1` in the app for the offline guide.
- Something not working? See {doc}`reference/troubleshooting`.
- Unfamiliar term? See the {doc}`reference/glossary`.
- Found a bug or have a board to share? Open an
  [issue on GitHub](https://github.com/MohamoudAli12/KiPI-SI/issues).

```{toctree}
:hidden:
:maxdepth: 2

getting-started/index
interface/index
dc/index
ac/index
noise/index
si/index
workflows
theory/index
reference/index
development/index
```
