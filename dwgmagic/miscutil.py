"""Preprocessing utilities operating on explicit project context."""
from __future__ import annotations

import shutil
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from dwgmagic.core.context import ProjectContext


@dataclass(slots=True)
class Preprocessor:
    """Prepares the project directory for processing."""

    def preprocess(self, context: ProjectContext, logger) -> List[str]:
        project_root = context.project_root
        dwg_files = self._collect_dwg_files(project_root)
        if not dwg_files:
            raise RuntimeError("No DWG files found in project root")

        self._cleanup_previous_run(project_root, logger)
        self._cleanup_logs(project_root / context.settings.log_dir, logger)
        self._ensure_directories(project_root, ("scripts", "originals", "derevitized"))
        self._archive_and_copy(project_root, dwg_files, logger)
        return dwg_files

    def _collect_dwg_files(self, root: Path) -> List[str]:
        return sorted(
            entry.name for entry in root.iterdir() if entry.suffix.lower() == ".dwg" and entry.is_file()
        )

    def _cleanup_previous_run(self, root: Path, logger) -> None:
        originals = root / "originals"
        if not originals.exists():
            return
        for entry in root.iterdir():
            if entry.name == "originals":
                continue
            if entry.is_dir():
                shutil.rmtree(entry, ignore_errors=True)
            else:
                entry.unlink(missing_ok=True)
        for entry in originals.iterdir():
            destination = root / entry.name
            shutil.copy(entry, destination)
        shutil.rmtree(originals, ignore_errors=True)
        logger.info("Previous preprocessing artifacts removed")

    def _ensure_directories(self, root: Path, directories: Iterable[str]) -> None:
        for directory in directories:
            (root / directory).mkdir(exist_ok=True)

    def _archive_and_copy(self, root: Path, files: Iterable[str], logger) -> None:
        originals = root / "originals"
        derevitized = root / "derevitized"
        count = 0
        for file_name in files:
            src = root / file_name
            shutil.copy(src, originals / file_name)
            shutil.copy(src, derevitized / file_name)
            src.unlink()
            count += 1
        logger.info("Copied %d DWG files", count)

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

