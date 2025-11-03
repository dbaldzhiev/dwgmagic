"""Preprocessing utilities operating on explicit project context."""
from __future__ import annotations

import shutil
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from dwgmagic.core.context import ProjectContext


@dataclass(slots=True)
class Preprocessor:
    """Prepares the project directory for processing."""

    def preprocess(self, context: ProjectContext, logger) -> List[str]:
        project_root = context.project_root
        dwg_files, from_originals = self._collect_dwg_files(project_root)
        if not dwg_files:
            raise RuntimeError("No DWG files found in project root")

        self._cleanup_previous_run(project_root, from_originals, logger)
        self._cleanup_logs(project_root / context.settings.log_dir, logger)
        self._ensure_directories(project_root, ("scripts", "originals", "derevitized"))
        self._populate_working_directories(project_root, dwg_files, from_originals, logger)
        return [path.name for path in dwg_files]

    def _collect_dwg_files(self, root: Path) -> Tuple[List[Path], bool]:
        root_files = sorted(
            entry for entry in root.iterdir() if entry.suffix.lower() == ".dwg" and entry.is_file()
        )
        if root_files:
            return root_files, False

        originals = root / "originals"
        if originals.exists():
            original_files = sorted(
                entry for entry in originals.iterdir() if entry.suffix.lower() == ".dwg" and entry.is_file()
            )
            if original_files:
                return original_files, True

        return [], False

    def _cleanup_previous_run(self, root: Path, rerun: bool, logger) -> None:
        originals = root / "originals"
        if rerun and originals.exists():
            logger.info("Detected previous run; restoring project from originals")

            preserved_suffixes = {".toml", ".tml", ".yaml", ".yml", ".json"}
            preserved_names = {"originals"}

            for entry in root.iterdir():
                if entry.name in preserved_names:
                    continue
                if entry.is_file() and entry.suffix.lower() in preserved_suffixes:
                    continue
                if entry.is_dir():
                    shutil.rmtree(entry, ignore_errors=True)
                else:
                    entry.unlink(missing_ok=True)
            logger.info("Previous preprocessing artifacts removed")
        else:
            # Remove known artifact directories if present without touching DWG sources.
            for directory in ("scripts", "derevitized", "logs"):
                target = root / directory
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target, ignore_errors=True)
                    else:
                        target.unlink(missing_ok=True)

    def _ensure_directories(self, root: Path, directories: Iterable[str]) -> None:
        for directory in directories:
            (root / directory).mkdir(exist_ok=True)

    def _populate_working_directories(
        self, root: Path, files: Sequence[Path], from_originals: bool, logger
    ) -> None:
        originals = root / "originals"
        derevitized = root / "derevitized"

        count = 0
        if from_originals:
            for source in files:
                shutil.copy(source, derevitized / source.name)
                count += 1
            logger.info("Restored %d DWG files from originals", count)
        else:
            self._clear_directory(originals)
            for source in files:
                destination_original = originals / source.name
                shutil.copy(source, destination_original)
                shutil.copy(source, derevitized / source.name)
                source.unlink()
                count += 1
            logger.info("Copied %d DWG files", count)

    def _clear_directory(self, directory: Path) -> None:
        if not directory.exists():
            return
        for entry in directory.iterdir():
            if entry.is_dir():
                shutil.rmtree(entry, ignore_errors=True)
            else:
                entry.unlink(missing_ok=True)

    def _cleanup_logs(self, log_dir: Path, logger) -> None:
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = log_dir.with_name(f"{log_dir.name}_backup_{timestamp}")
        try:
            log_dir.rename(backup_dir)
        except OSError as exc:
            logger.info("Reusing existing log directory %s: %s", log_dir, exc)
            for entry in log_dir.iterdir():
                if entry.is_dir():
                    shutil.rmtree(entry, ignore_errors=True)
                else:
                    try:
                        entry.unlink()
                    except PermissionError as remove_exc:
                        logger.debug("Skipping locked log file %s: %s", entry, remove_exc)
                    except OSError as remove_exc:
                        logger.warning("Unable to remove %s: %s", entry, remove_exc)
        finally:
            log_dir.mkdir(parents=True, exist_ok=True)


__all__ = ["Preprocessor"]

