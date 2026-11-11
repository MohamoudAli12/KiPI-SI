# Installation

KiPI-SI runs two ways, from the same folder:

* **As a KiCad plugin**, the main way: click the **KiPI-SI** button in the PCB editor and KiPI-SI
  reads the board open there. For this, the KiPI-SI folder **must be in KiCad's plugins
  folder**, and KiCad installs its dependencies.
* **Standalone**: KiPI-SI started on its own, with its launcher, opens board files and needs
  no KiCad. The folder can be **anywhere**; the launcher installs the dependencies on the
  first start. It opens KiCad 7 to 10 board files (`.kicad_pcb`), ODB++ jobs, HyperLynx
  files (`.hyp`) and KiPI-SI snapshots (`.kipi_si.json.gz`). Reading CCE files is on the way
  ([#143](https://github.com/MohamoudAli12/KiPI-SI/issues/143)).

## As a KiCad plugin

### Requirements

* **KiCad 9.0 or later.** Developed on KiCad 10 and confirmed on KiCad 9. Before 9.0.3,
  KiCad cannot say which layers a plated pad has copper on, so pads are kept on every layer
  (KiPI-SI warns in its log), and 9.0.0 cannot report net classes.
* **Python 3.10 to 3.13**, the one KiCad runs plugins with (some dependencies have no
  prebuilt packages for Python 3.14 yet).
  * **Windows:** KiCad's own Python 3.11. Nothing to do.
  * **Linux:** KiCad uses the system Python. On a distribution with Python 3.14 (Ubuntu
    26.04, Fedora 43), pip has to compile some packages, which needs
    `sudo apt install build-essential python3-dev` or similar.
  * **macOS:** KiCad bundles Python 3.9, which is too old. Install Python 3.12 (for
    example from python.org or Homebrew) and select it as the **Python interpreter** in
    *Preferences → Plugins*.

### Steps

1. In KiCad, enable **Preferences → Plugins → Enable KiCad API**.
2. Clone, link (or copy) this repo into your KiCad plugins folder, or uncompress the release source zip. The examples use KiCad 10's
   folder: for KiCad 9, put `9.0` in place of `10.0`. On Windows, KiCad uses your
   *Documents* folder, which may be redirected to OneDrive:

   ```powershell
   $plug = "$([Environment]::GetFolderPath('MyDocuments'))\KiCad\10.0\plugins"
   New-Item -ItemType Junction -Path "$plug\KiPI-SI" -Target "<path to this repo>"
   ```

   On macOS the folder is `~/Documents/KiCad/10.0/plugins`, and on Linux
   `~/.local/share/kicad/10.0/plugins`:

   ```sh
   ln -s "<path to this repo>" ~/Documents/KiCad/10.0/plugins/KiPI-SI          # macOS
   ln -s "<path to this repo>" ~/.local/share/kicad/10.0/plugins/KiPI-SI       # Linux
   ```

   Or, without git, download `KiPI-SI-<version>.zip` from the
   [latest release](https://github.com/MohamoudAli12/KiPI-SI/releases/latest) and unzip it into the
   plugins folder, which gives `plugins/KiPI-SI`.

3. Restart the PCB editor. KiCad builds the plugin venv in the background; the first time this
   downloads PySide6 and VTK, so give it a few minutes. The **KiPI-SI** toolbar button appears
   once the venv is ready. If it never appears, right-click the action in
   *Preferences → Plugins* and choose *Recreate Plugin Environment*.

## Standalone

1. Install **Python 3.10 to 3.13** if you do not have one (from
   [python.org](https://www.python.org/downloads/), or your package manager). On Linux, add
   `python3-venv` (Debian, Ubuntu) and, for the setup window, `python3-tk`.
2. Put the KiPI-SI folder anywhere: clone this repo, or unzip `KiPI-SI-<version>.zip` from the
   [latest release](https://github.com/MohamoudAli12/KiPI-SI/releases/latest).
3. Start KiPI-SI with its launcher: double-click **`kipi_si_launcher.pyw`** (Windows), or run

   ```sh
   python kipi_si_launcher.py                      # or: python kipi_si_launcher.py <board>.kipi_si.json.gz
   ```

   On Windows the first start leaves a **KiPI-SI** shortcut next to it. On Linux and macOS, run
   `python3 kipi_si_launcher.py --create-shortcut` once to add KiPI-SI to the applications menu
   (Linux) or `~/Applications` (macOS).

The first start sets up KiPI-SI. The setup window lists every package KiPI-SI will install with
its size (about 254 MB to download on Windows), and nothing is installed until you click
**Install**. On Windows and Linux x86-64 it also offers
[PARDISO](#optional-faster-solves-on-large-boards-windows-and-linux-x86-64). Everything goes
into an environment of KiPI-SI's own, outside the KiPI-SI folder (`KIPI_SI_HOME` puts it elsewhere):

| | KiPI-SI's environment |
|---|---|
| Windows | `%LOCALAPPDATA%\KiPI-SI` |
| macOS | `~/Library/Application Support/KiPI-SI` |
| Linux | `~/.local/share/kipi_si` |

![The launcher's setup window on a first start: every package with its size, and the optional PARDISO solver](/images/launcher_setup.png)

Use **Open…** to open a board and **Reload** to read it again. KiCad boards keep the same
setup file standalone and in the plugin. KiPI-SI uses the zone fills saved in the file, so
**fill the zones in KiCad (B) and save** before opening a `.kicad_pcb`. ODB++ jobs and
HyperLynx files share a board's setup when exported next to it with the same name
(`Board.zip`, `Board.hyp`). The {doc}`user guide </getting-started/overview>` lists what each format does
and does not carry.

To change the setup later, use **About → Manage dependencies…** in KiPI-SI, or the launcher:

```sh
python kipi_si_launcher.py --setup              # the setup window again (add or remove PARDISO)
python kipi_si_launcher.py --add-pardiso        # or --remove-pardiso, without questions
python kipi_si_launcher.py --repair             # reinstall everything from scratch
python kipi_si_launcher.py --reset              # delete KiPI-SI's environment
python kipi_si_launcher.py --create-shortcut    # add KiPI-SI to the Start menu / app menu / ~/Applications
```

If setup fails, the launcher says why; everything the installer printed is in the `logs`
folder next to the environment.

## Optional: faster solves on large boards (Windows and Linux, x86-64)

If the optional [`pypardiso`](https://pypi.org/project/pypardiso/) package is installed,
KiPI-SI solves with Intel MKL's multithreaded PARDISO solver in place of SciPy's
single-threaded one. On a 645k-unknown rail one solve drops from about 8 s to 1.2 s. Small
boards gain little. It costs about 210 MB of download on Windows (320 MB on Linux) and
there are no MKL packages for macOS or ARM.

The KiCad plugin gets it with its other requirements, installed by KiCad into the plugin's
environment. Standalone, the launcher's first setup installs it by default, with an
opt-out. *About → Manage dependencies…* adds or removes it later (in the plugin, removed it
is also left unused, since KiCad puts it back when it reloads the plugin), and *About → Copy version info* shows which solver is in use. If
PARDISO cannot load, KiPI-SI falls back to SciPy and says so in the log.
