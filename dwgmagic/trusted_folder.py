"""Trusted folder checking utilities."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from dwgmagic.settings import Settings


class TrustedFolderChecker:
    """Validates the trusted folder configuration using AutoCAD console."""

    def __init__(self, runner: "AutoCadRunnerProtocol") -> None:
        self._runner = runner

    def check(self, settings: Settings, logger) -> None:
        script_path = settings.tectonica_path / settings.trusted_folder_script
        if not script_path.exists():
            raise FileNotFoundError(script_path)
        result = self._runner.run_script(script_path=script_path, logger=logger)
        if not result.succeeded:
            raise RuntimeError("Trusted folder validation failed")


class AutoCadRunnerProtocol:
    """Protocol subset used for type-checking."""

    def run_script(self, script_path: Path, logger, input_path: Optional[Path] = None) -> "AutoCadResult":  # pragma: no cover - interface
        raise NotImplementedError


__all__ = ["TrustedFolderChecker"]

