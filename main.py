"""CLI entrypoint for the DWGMAGIC pipeline."""
from __future__ import annotations

import argparse
from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader
from rich.console import Console

from dwgmagic.core.context import ProjectConfig, ProjectContext
from dwgmagic.core.pipeline import PipelineRunner
from dwgmagic.core.stages import (
    AutoCadStage,
    PreprocessorStage,
    ScriptGenerationStage,
    TrustedFolderCheckStage,
)
from dwgmagic.integrations.autocad import AutoCadCoordinator, AutoCadRunner
from dwgmagic.logger import LoggerFactory
from dwgmagic.miscutil import Preprocessor
from dwgmagic.script_generator import ScriptGenerator
from dwgmagic.settings import Settings, load_settings
from dwgmagic.trusted_folder import TrustedFolderChecker

console = Console()


def build_environment(settings: Settings) -> Environment:
    search_paths = [str(path) for path in settings.resolve_template_roots()]
    loader = ChoiceLoader([FileSystemLoader(search_paths)])
    return Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DWGMAGIC Toolset")
    parser.add_argument("path", help="Path to the project directory")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--config", type=Path, help="Optional configuration file", default=None)
    parser.add_argument(
        "--template-root",
        action="append",
        type=Path,
        dest="template_roots",
        help="Additional template search path (can be specified multiple times)",
    )
    parser.add_argument("--autocad-path", type=Path, help="Explicit path to accoreconsole.exe")
    return parser.parse_args()


def display_title_bar() -> None:
    console.print("╭──────────────────────────────────────────────╮", style="cyan")
    console.print("│                   [bold magenta]DWGMAGIC[/bold magenta]                   │")
    console.print("├──────────────────────────────────────────────┤", style="cyan")
    console.print("│        [italic]TECTONICA - Dimitar Baldzhiev[/italic]         │")
    console.print("╰──────────────────────────────────────────────╯", style="cyan")


def main() -> None:
    args = parse_args()
    project_root = Path(args.path).resolve()
    settings = load_settings(
        project_root,
        verbose=args.verbose,
        config_file=args.config,
        template_roots=args.template_roots,
        autocad_path=args.autocad_path,
    )
    environment = build_environment(settings)

    logger_factory = LoggerFactory(settings)
    runner = AutoCadRunner(settings)
    coordinator = AutoCadCoordinator(runner)

    display_title_bar()

    stages = (
        TrustedFolderCheckStage(TrustedFolderChecker(runner), logger_factory),
        PreprocessorStage(Preprocessor(), logger_factory),
        ScriptGenerationStage(ScriptGenerator(environment), logger_factory),
        AutoCadStage(coordinator, logger_factory),
    )

    config = ProjectConfig(settings=settings, stages=[stage.name for stage in stages])
    context = ProjectContext(config=config, environment=environment)

    pipeline = PipelineRunner.from_iterable(stages)
    results = pipeline.run(context)

    for result in results:
        status = "✅" if result.succeeded else "❌"
        message = f"{status} {result.name}"
        if result.details and not result.succeeded:
            message = f"{message}: {result.details}"
        console.print(message)
        if not result.succeeded:
            break


if __name__ == "__main__":
    main()

