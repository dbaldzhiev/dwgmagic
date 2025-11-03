"""AutoCAD integration layer with structured execution and progress reporting."""
from __future__ import annotations

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, Sequence, Tuple

from dwgmagic.settings import Settings


@dataclass(slots=True)
class AutoCadResult:
    name: str
    returncode: int
    stdout: str
    stderr: str
    command: Tuple[str, ...]

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
        logger.info("Starting AutoCAD job for %s", script_path.name)
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
            command=tuple(command),
        )
        if not result.succeeded:
            logger.error("AutoCAD command failed (%s): %s", completed.returncode, completed.stderr)
        else:
            logger.debug("AutoCAD job %s completed successfully", script_path.stem)
        if result.stdout:
            logger.debug("%s stdout:%s%s", script_path.stem, os.linesep, result.stdout.strip())
        if result.stderr:
            logger.debug("%s stderr:%s%s", script_path.stem, os.linesep, result.stderr.strip())
        return result


class AutoCadCoordinator:
    """Coordinates execution of AutoCAD jobs using a thread pool."""

    def __init__(self, runner: AutoCadRunner, *, max_workers: Optional[int] = None) -> None:
        self.runner = runner
        self.max_workers = max_workers

    def execute(
        self,
        jobs: Sequence[AutoCadJob],
        logger,
        *,
        listener: Optional["AutoCadProgressListener"] = None,
    ) -> Sequence[AutoCadResult]:
        results: list[AutoCadResult] = []
        for job in jobs:
            _notify(listener, "on_job_queued", job)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {
                executor.submit(self._execute_job, job, logger, listener): job for job in jobs
            }
            for future in as_completed(future_map):
                job = future_map[future]
                try:
                    result = future.result()
                except Exception as exc:  # pragma: no cover - surface runtime failure
                    logger.error("Job %s failed: %s", job.name, exc)
                    _notify(listener, "on_job_failed", job, exc)
                    raise
                else:
                    logger.info("Job %s completed with code %s", job.name, result.returncode)
                    _notify(listener, "on_job_completed", result)
                    results.append(result)
        return results

    def _execute_job(
        self,
        job: AutoCadJob,
        logger,
        listener: Optional["AutoCadProgressListener"],
    ) -> AutoCadResult:
        _notify(listener, "on_job_started", job)
        return self.runner.run_script(
            script_path=job.script_path,
            input_path=job.input_path,
            logger=logger,
        )


class AutoCadProgressListener(Protocol):
    """Observer for AutoCAD job execution."""

    def on_job_queued(self, job: AutoCadJob) -> None:  # pragma: no cover - interface
        ...

    def on_job_started(self, job: AutoCadJob) -> None:  # pragma: no cover - interface
        ...

    def on_job_completed(self, result: AutoCadResult) -> None:  # pragma: no cover - interface
        ...

    def on_job_failed(self, job: AutoCadJob, error: Exception) -> None:  # pragma: no cover - interface
        ...


def _notify(listener: Optional[AutoCadProgressListener], method: str, *args) -> None:
    if listener is None:
        return
    callback = getattr(listener, method, None)
    if callable(callback):
        callback(*args)


__all__ = [
    "AutoCadResult",
    "AutoCadJob",
    "AutoCadRunner",
    "AutoCadCoordinator",
    "AutoCadProgressListener",
]
