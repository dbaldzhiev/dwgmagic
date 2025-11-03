"""AutoCAD integration layer with structured execution."""
from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

from dwgmagic.settings import Settings


@dataclass(slots=True)
class AutoCadResult:
    name: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0


@dataclass(slots=True)
class AutoCadJob:
    name: str
    script_path: Path
    input_path: Optional[Path]


class AutoCadRunner:
    """Executes AutoCAD console commands with error handling."""

    def __init__(self, settings: Settings, *, timeout: Optional[int] = None) -> None:
        self.settings = settings
        self.timeout = timeout

    def discover(self) -> Path:
        if self.settings.autocad_executable and self.settings.autocad_executable.exists():
            return self.settings.autocad_executable
        for candidate in self.settings.autocad_candidates:
            if candidate.exists():
                return candidate
        raise FileNotFoundError("Unable to locate accoreconsole.exe")

    def run_script(
        self,
        *,
        script_path: Path,
        logger,
        input_path: Optional[Path] = None,
    ) -> AutoCadResult:
        executable = self.discover()
        command = [str(executable)]
        if input_path is not None:
            command.extend(["/i", str(input_path)])
        command.extend(["/s", str(script_path)])
        logger.debug("Executing %s", command)
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-16-le",
            timeout=self.timeout,
            check=False,
        )
        result = AutoCadResult(
            name=script_path.stem,
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )
        if not result.succeeded:
            logger.error("AutoCAD command failed (%s): %s", completed.returncode, completed.stderr)
        return result


class AutoCadCoordinator:
    """Coordinates execution of AutoCAD jobs using a thread pool."""

    def __init__(self, runner: AutoCadRunner, *, max_workers: Optional[int] = None) -> None:
        self.runner = runner
        self.max_workers = max_workers

    def execute(self, jobs: Sequence[AutoCadJob], logger) -> List[AutoCadResult]:
        results: List[AutoCadResult] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {
                executor.submit(
                    self.runner.run_script,
                    script_path=job.script_path,
                    input_path=job.input_path,
                    logger=logger,
                ): job
                for job in jobs
            }
            for future in as_completed(future_map):
                job = future_map[future]
                try:
                    result = future.result()
                except Exception as exc:  # pragma: no cover - surface runtime failure
                    logger.error("Job %s failed: %s", job.name, exc)
                    raise
                else:
                    logger.info("Job %s completed with code %s", job.name, result.returncode)
                    results.append(result)
        return results


__all__ = ["AutoCadResult", "AutoCadJob", "AutoCadRunner", "AutoCadCoordinator"]

