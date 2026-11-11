# Development

The project is managed with [uv](https://docs.astral.sh/uv/). From a checkout, KiPI-SI runs
standalone, or as the plugin against the running PCB editor:

```sh
uv sync                                        # .venv from uv.lock: the plugin's packages and the dev tools
uv run python -m kipi_si tests/data/synthetic.kipi_si.json   # standalone, opening a board
KIPI_SI_HOST=plugin uv run python -m kipi_si   # the plugin: connect to KiCad
uv run python -m kipi_si --dump board.kipi_si.json.gz        # extract from KiCad only, no window
uv run pytest tests
uv run ruff check .                            # lint, as CI does (ruff check . --fix fixes most)
```

On Windows PowerShell, set the variable first: `$env:KIPI_SI_HOST = "plugin"; uv run python -m kipi_si`.
`uv sync -p 3.11` builds the environment on another Python, such as the one your KiCad runs.

Dependencies live in `pyproject.toml`: `dependencies` for standalone, the `kicad` extra for the
plugin, and the `lint`, `test` and `dev` groups for development. Add or change one with
`uv add` (`uv add --group test ...` for a tool) and commit the updated `uv.lock`; CI fails
if the lock is out of date. KiCad and the launcher do not use uv: `requirements.txt` is what
KiCad installs into the plugin's venv and `requirements-standalone.txt` what the launcher
installs, so update them by hand. `tests/core/test_requirements.py` keeps them in step with
`pyproject.toml`. After changing them, run `uv run python .github/scripts/dep_sizes.py`.
CI installs `requirements.txt` as KiCad does, with the newest versions it allows rather than
the lock's, so a dependency's new release that breaks KiPI-SI shows up there first.

The tests follow the package (`tests/core`, `tests/dc`, `tests/ac`, `tests/noise`,
`tests/sources`, `tests/gui`, `tests/scripts`). `tests/accuracy` solves the boards in
[`examples/validation`](https://github.com/MohamoudAli12/KiPI-SI/blob/main/examples/validation) and compares the results with hand
calculations, to help gain confidence that an open-source tool can compare to professional
tools:

| Board | Checks |
|---|---|
| `skinny_traces` | 0.15 mm and 0.1 mm tracks on outer and inner layers (ρL/wt), an arc track (annular sector) |
| `right_angle` | an L route and a Z route: 0.5587 squares per right-angle corner |
| `layer_change` | a strip dropping from F.Cu to In2.Cu through a row of vias: barrels in parallel, current crowding, equal sharing |
| `planes` | two pads on a disc-shaped inner plane (method of images); one strip on two layers of different weights |
| `power_chain` | source, switcher, ferrite series link and remote-sensed LDO over a ground strip: every voltage and current |
| `ac_plane` | plane-pair capacitance ε₀εrA/h and the first cavity resonance c/(2a√εr) |
| `ac_decap` | a mounted capacitor as a series RLC: low-frequency capacitance, mounted inductance, ESR at resonance |
| `ac_ferrite` | a ferrite (R + L link) feeding a small plane: lumped impedance and its LC resonance |

After changing a board there, rerun `python examples/validation/make_boards.py [name]` (or
`python examples/multiphase_buck/make_board.py` for the example) and commit its files.

CI runs ruff and the test suite for every push and pull request on Windows, Linux (Python
3.10 to 3.13) and macOS; the accuracy tests run for pull requests into `main`.
`tests/helpers/kicad_fake.py` stands in for each KiCad version from 9.0.0 to 10.0.6.

```{toctree}
:maxdepth: 1

codebase
building-docs
license
```
