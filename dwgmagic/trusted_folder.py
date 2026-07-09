"""Trusted folder checking utilities."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from dwgmagic.errors import TrustedFolderError
from dwgmagic.settings import Settings


class TrustedFolderChecker:
    """Validates that AutoCAD can NETLOAD tectonica.dll from the app folder.

    The check script is generated at runtime so it always points at the
    configured ``tectonica_path`` instead of a hardcoded location.
    """

    def __init__(self, runner: "AutoCadRunnerProtocol") -> None:
        self._runner = runner

    def check(self, settings: Settings, logger) -> None:
        dll_path = settings.tectonica_path / "tectonica.dll"
        if not dll_path.exists():
            raise TrustedFolderError(
                f"tectonica.dll not found at {dll_path}",
                hint="Run build_tectonica.ps1 (or reinstall) to produce the plugin DLL.",
            )

        script_path = self._resolve_script(settings)
        result = self._runner.run_script(script_path=script_path, logger=logger)
        if not result.succeeded:
            reason = getattr(result, "failure_reason", None) or f"exit code {result.returncode}"
            raise TrustedFolderError(
                f"Trusted folder validation failed ({reason})",
                hint=(
                    f"Add {settings.tectonica_path} to AutoCAD's trusted locations "
                    "(OPTIONS > Files > Trusted Locations, or the TRUSTEDPATHS variable)."
                ),
            )

    def _resolve_script(self, settings: Settings) -> Path:
        """Use a pre-existing check script if present, else generate one."""

        static_script = settings.tectonica_path / settings.trusted_folder_script
        if static_script.exists():
            return static_script

        dll = (settings.tectonica_path / "tectonica.dll").as_posix()
        handle = tempfile.NamedTemporaryFile(
            "w",
            suffix=".scr",
            prefix="dwgmagic_trusted_",
            delete=False,
            encoding=settings.script_encoding,
            errors="replace",
        )
        with handle as fh:
            fh.write(f'netload "{dll}"\n')
        return Path(handle.name)


class AutoCadRunnerProtocol:
    """Protocol subset used for type-checking."""

    def run_script(self, script_path: Path, logger, input_path: Optional[Path] = None) -> "AutoCadResult":  # pragma: no cover - interface
        raise NotImplementedError


__all__ = ["TrustedFolderChecker"]
