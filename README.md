# DWGMAGIC

DWGMAGIC automates the end-to-end workflow for converting batches of Revit-exported DWG files into a single deliverable package.  
The modernised architecture replaces historical global state with an explicit pipeline that can be monitored from either the CLI or a Tkinter-based GUI.

## Key Features
- **Pipeline orchestration** – Trusted-folder validation, preprocessing, script generation, and AutoCAD execution run as discrete stages with shared context.
- **Resilient AutoCAD execution** – Structured job objects, safe subprocess handling, and sequential batching guarantee that merge jobs only run after sheet outputs exist.
- **Interactive monitoring** – Rich-based CLI progress reporter plus an enhanced GUI that streams stage status, AutoCAD job details, and live logs.
- **Rerun aware preprocessing** – Automatically cleans previous artefacts while preserving the `originals/` folder so projects can be processed multiple times without manual cleanup.

## Installation
### Core requirements
1. **Install Python 3.10+** on the machine that hosts AutoCAD.
2. **Install dependencies** (from the project root):
   ```bash
   python -m pip install -r requirements.txt
   ```
3. **Ensure AutoCAD is available** – the tool locates `accoreconsole.exe` using the configured search paths in `dwgmagic/settings.py` or via the `--autocad-path` CLI flag.
4. *(Optional)* add the repository folder to AutoCAD’s trusted locations.

### Windows desktop integration
The repository now ships with helper scripts that set up shortcuts and shell integration for a smoother workflow on Windows:
1. Run `install.bat` to copy the project into `%LOCALAPPDATA%\dwgmagic`, register a **Run with DWGMAGIC** context-menu entry for directories, and create a desktop shortcut that launches the GUI (`run_gui.bat`). If `robocopy` encounters a critical error (for example, exit code 16), the installer now prints the captured log and automatically retries the copy by using PowerShell so that the installation can still complete.
2. After installation you can either double-click the desktop shortcut for the GUI or right-click any project directory and choose **Run with DWGMAGIC** to execute the CLI pipeline via `run_context_menu.bat`.
3. To remove the integration, run `uninstall.bat`. This removes the context-menu entry, deletes the desktop shortcut, and wipes the installed copy under `%LOCALAPPDATA%\dwgmagic`.

## Usage
### Command-line interface
```bash
python main.py <project_directory> [--verbose] [--config path/to/settings.toml]
```
Common flags:
- `--template-root PATH` – supply additional template search roots.
- `--autocad-path PATH` – point directly to `accoreconsole.exe`.
- `--verbose` – stream detailed logs to the terminal.

### Graphical interface
```bash
python main.py <project_directory> --gui
```
The GUI displays:
- Stage progress with automatic completion tracking.
- A detailed AutoCAD job table including script names, live status updates, and return codes.
- Streaming log output for deep troubleshooting.
Use the **Run Pipeline** button to start the process; the interface becomes interactive again once execution completes.

## Configuration
Runtime settings are encapsulated by the [`Settings` dataclass](dwgmagic/settings.py). Configuration values can be supplied by:
1. CLI flags (highest precedence).
2. A TOML/YAML file provided via `--config`.
3. Environment variables (see `load_settings` in `dwgmagic/settings.py`).
The configuration controls AutoCAD discovery, template search paths, logging behaviour, and feature toggles.

## Project Structure
- `dwgmagic/core/` – pipeline primitives and stage implementations.
- `dwgmagic/integrations/` – AutoCAD runner/coordinator abstractions.
- `dwgmagic/gui/` – Tkinter application for monitoring runs visually.
- `dwgmagic/ui/` – shared listeners for CLI and GUI progress reporting.
- `templates/` – packaged Jinja templates used to generate AutoCAD scripts.

## Testing
Run the full test suite with:
```bash
pytest
```
The tests cover configuration precedence, preprocessing reruns, script generation, AutoCAD job orchestration, and pipeline control flow.

## Contributing & Support
Issues and pull requests are welcome. When reporting bugs, include:
- The command you ran (CLI arguments or GUI launch instructions).
- Relevant log snippets from `logs/` or the GUI Activity pane.
- AutoCAD return codes, if applicable.

For day-to-day usage guidance, see the comments at the top of `main.py` and the logging output produced during runs.
