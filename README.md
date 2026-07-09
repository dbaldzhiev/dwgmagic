# DWGMAGIC

DWGMAGIC automates the end-to-end workflow for converting batches of Revit-exported DWG files into a single deliverable package.
The pipeline (trusted-folder validation → preprocessing → script generation → AutoCAD console execution) can be driven from a full-featured GUI (the default) or a headless CLI.

## Key Features
- **Pipeline orchestration** — discrete stages with shared context, per-stage timing, and structured results.
- **Resilient AutoCAD execution** — bounded parallelism, per-job timeouts, live console output streaming, cancellation, and failure detection that catches jobs which "succeed" with a zero exit code but fail in their output.
- **Output validation** — sheet batches must actually produce their `*_xrefed.dwg` files before the merge is attempted; the final deliverables (`<project>_MXR.dwg`, `<project>_MM.dwg`) are verified and reported with sizes.
- **Safety guardrails** — preprocessing refuses to touch folders that don't look like DWGMAGIC projects, and the GUI asks for confirmation before the first run in a folder.
- **Run tracking** — every run writes a chronological `logs/run.log`, per-job console dumps under `logs/jobs/`, and a machine-readable manifest `logs/run_<timestamp>.json` (settings, stages, jobs, durations, deliverables).
- **Auto-update** — the GUI checks GitHub releases on startup and can update itself in place; `update.bat` works standalone too.

## Installation

### End users (Windows)
1. Download the latest release zip (or clone the repo) and unpack it anywhere.
2. Make sure `tectonica.dll` is present in the folder (ships with releases built locally; otherwise see [Building tectonica.dll](#building-tectonicadll)).
3. Run `install.bat`. It will:
   - copy the application to `%LOCALAPPDATA%\dwgmagic`,
   - create a private Python virtual environment and install all dependencies (requires Python 3.10+ on PATH),
   - register **Run with DWGMAGIC** in the right-click menu of folders (and folder backgrounds),
   - create a desktop shortcut that opens the GUI.
4. Launch from the desktop shortcut, or right-click a project folder → **Run with DWGMAGIC** (opens the GUI preloaded and starts the run).

To remove everything, run `uninstall.bat` (removes the context-menu entries, desktop shortcut, and the installed copy).

### Developers (from source)
```bash
git clone --recurse-submodules https://github.com/dbaldzhiev/dwgmagic.git
cd dwgmagic
python -m pip install -r requirements.txt   # or: pip install -e .[gui,dev]
python main.py                              # opens the GUI
```
The [tectonica](https://github.com/dbaldzhiev/tectonica) AutoCAD plugin is a git submodule under `vendor/tectonica`; run `git submodule update --init --recursive` if you cloned without `--recurse-submodules`.

## Updating

- **From the GUI** — when a newer GitHub release exists, an **Update to vX.Y.Z** button appears in the sidebar. Clicking it closes the app, applies the update, reinstalls dependencies, and relaunches.
- **Manually** — run `update.bat` in the application folder. Git checkouts are updated with `git pull --ff-only`; installed copies download the latest release archive. The updater preserves `venv/`, `logs/`, and your locally built `tectonica.dll`.
- Set the environment variable `DWGMAGIC_CHECK_UPDATES=0` (or pass `--no-update-check`) to disable the startup check.

## Usage

### GUI (default)
```bash
python main.py [project_directory]
```
Opens the pipeline monitor. Features:
- Open a project via the button, the recent-projects list, or by dropping a folder onto the window.
- Preflight checks for AutoCAD, the tectonica.dll plugin, and the trusted-path configuration.
- Stage table with per-stage timing; task tree with per-job status, exit codes, durations, and **live AutoCAD console output**.
- **Cancel Run** button that stops scheduling new jobs and kills running AutoCAD consoles.
- A run summary (deliverables + sizes, failed jobs with reasons) at the end of every run.
- Light/Dark/System appearance; window size, appearance, and recent projects persist between sessions.

`--autorun` starts the pipeline automatically once the project loads (used by the context-menu integration).

### CLI (headless)
```bash
python main.py <project_directory> --cli [--verbose] [--config path/to/settings.toml]
```
Prints stage progress and a run summary; the exit code is `0` on success, `1` on failure, `130` when cancelled with Ctrl+C — suitable for scripting.

Common flags (both front-ends):
- `--template-root PATH` — additional template search roots (repeatable).
- `--autocad-path PATH` — explicit path to `accoreconsole.exe`.
- `--verbose` — stream detailed logs to the terminal.
- `--version` — print the application version.

## Configuration
Runtime settings are defined by the [`Settings` dataclass](dwgmagic/settings.py). Precedence: CLI flags > config file (`--config`, TOML/YAML) > environment variables > defaults.

| Setting | Env var | Default | Purpose |
| --- | --- | --- | --- |
| `autocad_executable` | `DWGMAGIC_AUTOCAD_PATH` | auto-discovered | Explicit `accoreconsole.exe` path. Discovery checks the registry, then `C:\Program Files\Autodesk\AutoCAD 2017–2026`. |
| `tectonica_path` | `DWGMAGIC_TECTONICA_PATH` | the app folder | Where `tectonica.dll` is NETLOADed from (relocatable). |
| `max_workers` | `DWGMAGIC_MAX_WORKERS` | `2` | Simultaneous AutoCAD console processes. |
| `job_timeout` | `DWGMAGIC_JOB_TIMEOUT` | `1800` | Seconds before a hung job is killed. |
| `continue_on_error` | `DWGMAGIC_CONTINUE_ON_ERROR` | `false` | Keep going when individual jobs fail. |
| `xref_xplode_toggle` | `DWGMAGIC_XREF_EXPLODE` | `true` | Use the tecbxt bind/explode path. |
| `template_roots` | `DWGMAGIC_TEMPLATE_ROOT` | bundled | Extra template search roots. |
| `log_dir` / `log_level` / `log_encoding` | `DWGMAGIC_LOG_DIR` / `_LOG_LEVEL` / `_LOG_ENCODING` | `logs` / `DEBUG` / `utf-8` | Logging behaviour. |
| `script_encoding` | — | `cp1251` | Encoding of generated `.scr` files. |
| `check_updates` | `DWGMAGIC_CHECK_UPDATES` | `true` | GitHub release check on GUI startup. |

## Building tectonica.dll
Generated `.scr` scripts `NETLOAD` `tectonica.dll` from the application folder; it is not committed to this repo and must be built from the `vendor/tectonica` submodule:
```powershell
./build_tectonica.ps1                 # builds Release config, copies tectonica.dll to the repo root
./build_tectonica.ps1 -Configuration Debug
```
tectonica targets AutoCAD 2025's managed API (`net8.0-windows`). Building requires:
- The ObjectARX 2025 managed reference assemblies (`AcCoreMgd.dll`, `AcDbMgd.dll`, `AcMgd.dll`, `AcDx.dll`, plus their dependents) copied from the ObjectARX 2025 SDK's `inc/` folder into `C:\Autodesk\ObjectARX2025\inc\` (the path referenced by `vendor/tectonica/tectonica/tectonica.csproj`).
- MSBuild (Visual Studio or Build Tools) and the .NET 8 SDK.

Because the ObjectARX SDK is proprietary, CI does **not** build the DLL; release archives contain only the Python application, and the updater deliberately preserves your locally built copy. Re-run `build_tectonica.ps1` whenever `vendor/tectonica` changes (`git submodule update --remote`).

## Troubleshooting a failed run
Inside the project folder:
- `logs/run.log` — chronological log of the whole run, all components.
- `logs/jobs/<script>.out.txt` — raw AutoCAD console output per job.
- `logs/run_<timestamp>.json` — the run manifest: settings snapshot, stage timings, per-job exit codes/durations/failure reasons, deliverable status.

The GUI shows the same information live (Tasks tab → select a job for its output).

## Project Structure
- `dwgmagic/core/` — pipeline primitives and stage implementations.
- `dwgmagic/integrations/` — AutoCAD runner/coordinator (subprocess management, discovery).
- `dwgmagic/gui/` — CustomTkinter application and persisted UI state.
- `dwgmagic/ui/` — shared progress listeners for CLI and GUI.
- `dwgmagic/templates/` — packaged Jinja templates for AutoCAD script generation.
- `dwgmagic/classify.py` — the single source of truth for the sheet/view file-naming convention.
- `dwgmagic/manifest.py` — run manifests and summaries.
- `dwgmagic/update.py` — GitHub release update checks.

## Testing & CI
```bash
pytest
```
GitHub Actions runs the test suite on every push/PR (`.github/workflows/ci.yml`). Tagging `vX.Y.Z` (matching `dwgmagic.__version__`) creates a GitHub release with a source archive (`.github/workflows/release.yml`), which the in-app updater picks up.

## Contributing & Support
Issues and pull requests are welcome. When reporting bugs, include:
- The command you ran (CLI arguments or GUI launch instructions).
- The run manifest and relevant snippets from `logs/run.log`.
- AutoCAD job output from `logs/jobs/`, if applicable.
