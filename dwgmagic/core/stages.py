"""Concrete pipeline stages for DWGMAGIC."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from dwgmagic.core.pipeline import PipelineStage
from dwgmagic.integrations.autocad import AutoCadCoordinator, AutoCadJob
from dwgmagic.logger import LoggerFactory
from dwgmagic.miscutil import Preprocessor
from dwgmagic.script_generator import ScriptGenerator
from dwgmagic.trusted_folder import TrustedFolderChecker

from .context import ProjectContext, StageResult


@dataclass(slots=True)
class TrustedFolderCheckStage(PipelineStage):
    """Ensures the AutoCAD trusted folder is configured."""

    checker: TrustedFolderChecker
    logger_factory: LoggerFactory

    name: str = "trusted_folder_check"

    def run(self, context: ProjectContext) -> StageResult:
        logger = self.logger_factory.create("CHECKS")
        try:
            self.checker.check(context.settings, logger)
            return StageResult(self.name, True)
        except Exception as exc:  # pragma: no cover - thin wrapper
            logger.error("Trusted folder check failed: %s", exc)
            return StageResult(self.name, False, str(exc))


@dataclass(slots=True)
class PreprocessorStage(PipelineStage):
    """Cleans and prepares the project workspace."""

    preprocessor: Preprocessor
    logger_factory: LoggerFactory

    name: str = "preprocess"

    def run(self, context: ProjectContext) -> StageResult:
        logger = self.logger_factory.create("MISC_UTIL")
        try:
            dwg_files = self.preprocessor.preprocess(context, logger)
            context.set("dwg_files", dwg_files)
            return StageResult(self.name, True, data={"dwg_files": dwg_files})
        except Exception as exc:  # pragma: no cover - thin wrapper
            logger.error("Preprocessing failed: %s", exc)
            return StageResult(self.name, False, str(exc))


@dataclass(slots=True)
class ScriptGenerationStage(PipelineStage):
    """Generates AutoCAD scripts and batch files."""

    generator: ScriptGenerator
    logger_factory: LoggerFactory

    name: str = "generate_scripts"

    def run(self, context: ProjectContext) -> StageResult:
        logger = self.logger_factory.create("SCRIPT_GENERATOR")
        try:
            artifacts = self.generator.generate_all(context, logger)
            context.set("scripts", artifacts)
            return StageResult(self.name, True, data=artifacts)
        except Exception as exc:  # pragma: no cover - thin wrapper
            logger.error("Script generation failed: %s", exc)
            return StageResult(self.name, False, str(exc))


@dataclass(slots=True)
class AutoCadStage(PipelineStage):
    """Runs AutoCAD console jobs for views, sheets, and merge."""

    coordinator: AutoCadCoordinator
    logger_factory: LoggerFactory

    name: str = "autocad"

    def run(self, context: ProjectContext) -> StageResult:
        logger = self.logger_factory.create("AUTOCAD")
        try:
            state = self._build_jobs(context)
            results = self.coordinator.execute(state.jobs, logger)
            context.set("autocad_results", results)
            return StageResult(self.name, True, data={"results": results})
        except Exception as exc:  # pragma: no cover - thin wrapper
            logger.error("AutoCAD execution failed: %s", exc)
            return StageResult(self.name, False, str(exc))

    @dataclass(slots=True)
    class StageJobs:
        jobs: Sequence[AutoCadJob]

    def _build_jobs(self, context: ProjectContext) -> "AutoCadStage.StageJobs":
        project_root = context.project_root
        derevitized = project_root / "derevitized"
        scripts_dir = project_root / "scripts"

        dwg_files: Iterable[str] = context.get("dwg_files", [])
        view_files = [f for f in dwg_files if "-View-" in f]
        sheet_files = [
            f
            for f in dwg_files
            if f.endswith(".dwg") and "-View-" not in f and "-rvt-" not in f
        ]
        context.set("view_files", view_files)
        context.set("sheet_files", sheet_files)

        jobs: List[AutoCadJob] = []
        for view in view_files:
            jobs.append(
                AutoCadJob(
                    name=f"view:{Path(view).stem}",
                    script_path=scripts_dir / f"{Path(view).stem.upper()}.scr",
                    input_path=derevitized / view,
                )
            )

        for sheet in sheet_files:
            jobs.append(
                AutoCadJob(
                    name=f"sheet:{Path(sheet).stem}",
                    script_path=scripts_dir / f"{Path(sheet).stem.upper()}_SHEET.scr",
                    input_path=derevitized / sheet,
                )
            )

        jobs.append(
            AutoCadJob(
                name="merge",
                script_path=scripts_dir / "DWGMAGIC.scr",
                input_path=None,
            )
        )

        return AutoCadStage.StageJobs(tuple(jobs))

