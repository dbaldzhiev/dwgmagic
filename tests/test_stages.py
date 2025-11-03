from pathlib import Path
from types import SimpleNamespace

from jinja2 import DictLoader, Environment

from dwgmagic.core.context import ProjectConfig, ProjectContext
from dwgmagic.core.stages import (
    AutoCadStage,
    PreprocessorStage,
    ScriptGenerationStage,
    TrustedFolderCheckStage,
)
from dwgmagic.integrations.autocad import AutoCadResult
from dwgmagic.logger import LoggerFactory
from dwgmagic.miscutil import Preprocessor
from dwgmagic.script_generator import ScriptGenerator
from dwgmagic.settings import Settings
from dwgmagic.trusted_folder import TrustedFolderChecker


def make_context(tmp_path):
    settings = Settings(project_root=tmp_path, log_dir=Path("logs"))
    env = Environment(loader=DictLoader({}))
    config = ProjectConfig(settings=settings)
    return ProjectContext(config=config, environment=env), settings


def test_trusted_folder_check_stage(tmp_path):
    context, settings = make_context(tmp_path)
    tectonica = tmp_path / "tectonica"
    tectonica.mkdir()
    script = tectonica / settings.trusted_folder_script
    script.write_text("test")
    settings.tectonica_path = tectonica

    calls = {}

    def run_script(script_path, logger, input_path=None):
        calls["script_path"] = script_path
        return AutoCadResult(name="trusted", returncode=0, stdout="", stderr="")

    checker = TrustedFolderChecker(SimpleNamespace(run_script=run_script))
    stage = TrustedFolderCheckStage(checker, LoggerFactory(settings))
    result = stage.run(context)

    assert result.succeeded is True
    assert calls["script_path"] == script


def test_preprocessor_stage(tmp_path):
    context, settings = make_context(tmp_path)
    (tmp_path / "example.dwg").write_text("content")
    stage = PreprocessorStage(Preprocessor(), LoggerFactory(settings))
    result = stage.run(context)
    assert result.succeeded is True
    assert context.get("dwg_files") == ["example.dwg"]
    assert (tmp_path / "derevitized" / "example.dwg").exists()
    assert (tmp_path / "originals" / "example.dwg").exists()


def test_script_generation_stage(tmp_path):
    context, settings = make_context(tmp_path)
    context.set("dwg_files", ["SheetA.dwg", "SheetA-View-1.dwg"])
    env = Environment(
        loader=DictLoader(
            {
                "templates/project_script_template.tmpl": "{{ sheetNamesList|length }}",
                "templates/mmm_script_template.tmpl": "merge",
                "templates/manual_merge_bat_template.tmpl": "bat",
                "templates/view_script_template.tmpl": "view {{ viewName }}",
                "templates/sheet_script_template.tmpl": "sheet {{ sheetName }} {{ viewsOnSheet|length }}",
            }
        )
    )
    context.environment = env
    stage = ScriptGenerationStage(ScriptGenerator(env), LoggerFactory(settings))
    result = stage.run(context)
    assert result.succeeded is True
    assert (tmp_path / "scripts" / "DWGMAGIC.scr").read_text(encoding="cp1251") == "1"
    assert (tmp_path / "scripts" / "SHEETA_SHEET.scr").exists()
    assert (tmp_path / "scripts" / "SHEETA-VIEW-1.scr").exists()


def test_autocad_stage_builds_jobs(tmp_path):
    context, settings = make_context(tmp_path)
    context.set("dwg_files", ["SheetA.dwg", "SheetA-View-1.dwg"])
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "DWGMAGIC.scr").write_text("merge")
    (scripts_dir / "SHEETA-VIEW-1.scr").write_text("view")
    (scripts_dir / "SHEETA_SHEET.scr").write_text("sheet")
    (tmp_path / "derevitized").mkdir()
    (tmp_path / "derevitized" / "SheetA.dwg").write_text("sheet")
    (tmp_path / "derevitized" / "SheetA-View-1.dwg").write_text("view")

    class FakeCoordinator:
        def __init__(self):
            self.jobs = None

        def execute(self, jobs, logger):
            self.jobs = list(jobs)
            return [AutoCadResult(name=job.name, returncode=0, stdout="", stderr="") for job in jobs]

    coordinator = FakeCoordinator()
    stage = AutoCadStage(coordinator, LoggerFactory(settings))
    result = stage.run(context)
    assert result.succeeded is True
    assert [job.name for job in coordinator.jobs] == ["view:SheetA-View-1", "sheet:SheetA", "merge"]
