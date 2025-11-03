"""CLI entrypoint for the DWGMAGIC pipeline."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader
from rich.console import Console

from dwgmagic.core.context import ProjectConfig, ProjectContext
from dwgmagic.core.pipeline import PipelineRunner
from dwgmagic.core.stages import build_default_stages
from dwgmagic.integrations.autocad import AutoCadCoordinator, AutoCadRunner
from dwgmagic.logger import LoggerFactory
from dwgmagic.settings import Settings, load_settings
from dwgmagic.ui.progress import ConsoleProgressListener

console = Console()


def build_environment(settings: Settings) -> Environment:
    """Construct a Jinja environment with resilient template discovery."""

    seen = set()
    search_paths = []

    def _add_path(path: Path) -> None:
        path_str = str(path)
        if path_str not in seen:
            seen.add(path_str)
            search_paths.append(path_str)

    for root in settings.resolve_template_roots():
        _add_path(root)
        _add_path(root / "templates")

    # Always include the templates bundled with the application as a fallback.
    bundled_templates = Path(__file__).resolve().parent / "templates"
    _add_path(bundled_templates.parent)
    _add_path(bundled_templates)

    loaders = []
    if search_paths:
        loaders.append(FileSystemLoader(search_paths))

    try:  # pragma: no cover - exercised indirectly when package data is available
        loaders.append(PackageLoader("dwgmagic", "templates"))
    except Exception:
        pass

    if not loaders:
        raise RuntimeError("No template loaders could be configured")

    loader = loaders[0] if len(loaders) == 1 else ChoiceLoader(loaders)
    return Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DWGMAGIC Toolset")
    parser.add_argument("path", nargs="?", help="Path to the project directory")
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
    parser.add_argument("--gui", action="store_true", help="Launch the graphical interface")
    return parser.parse_args()


def display_title_bar() -> None:
    console.print("╭──────────────────────────────────────────────╮", style="cyan")
    console.print("│                   [bold magenta]DWGMAGIC[/bold magenta]                   │")
    console.print("├──────────────────────────────────────────────┤", style="cyan")
    console.print("│        [italic]TECTONICA - Dimitar Baldzhiev[/italic]         │")
    console.print("╰──────────────────────────────────────────────╯", style="cyan")


def main() -> None:
    args = parse_args()
    project_root = Path(args.path).resolve() if args.path else None

    if args.gui:
        from dwgmagic.gui.app import run_gui

        def _load_settings(root: Path) -> Settings:
            return load_settings(
                root,
                verbose=args.verbose,
                config_file=args.config,
                template_roots=args.template_roots,
                autocad_path=args.autocad_path,
            )

        run_gui(
            settings_loader=_load_settings,
            environment_builder=build_environment,
            runner_factory=lambda settings: AutoCadRunner(settings),
            coordinator_factory=lambda runner: AutoCadCoordinator(runner),
            logger_factory_builder=lambda settings: LoggerFactory(settings),
            initial_project=project_root,
        )
        return

    if project_root is None:
        console.print("[red]Error:[/red] Path to the project directory is required.")
        raise SystemExit(1)

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

    if settings.verbose:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, settings.log_level))
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger_factory = logger_factory.with_handlers(console_handler)

    stages = build_default_stages(environment, logger_factory, runner, coordinator)

    config = ProjectConfig(settings=settings, stages=[stage.name for stage in stages])
    context = ProjectContext(config=config, environment=environment)

    listener = ConsoleProgressListener(console)
    context.set("autocad_listener", listener)

    pipeline = PipelineRunner.from_iterable(stages)
    results = pipeline.run(context, listener=listener)

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

