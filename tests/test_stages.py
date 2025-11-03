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
        return AutoCadResult(name="trusted", returncode=0, stdout="", stderr="", command=(str(script_path),))

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


def test_preprocessor_stage_reruns_from_originals(tmp_path):
    context, settings = make_context(tmp_path)
    source = tmp_path / "rerun.dwg"
    source.write_text("content")
    stage = PreprocessorStage(Preprocessor(), LoggerFactory(settings))
    first_result = stage.run(context)
    assert first_result.succeeded is True

    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    (scripts_dir / "old.scr").write_text("old")
    derevitized_file = tmp_path / "derevitized" / "rerun.dwg"
    derevitized_file.write_text("stale")
    stale_root = tmp_path / "converted_output"
    stale_root.mkdir()
    (stale_root / "artifact.txt").write_text("old")

    rerun_context, rerun_settings = make_context(tmp_path)
    rerun_stage = PreprocessorStage(Preprocessor(), LoggerFactory(rerun_settings))
    rerun_result = rerun_stage.run(rerun_context)

    assert rerun_result.succeeded is True
    assert rerun_context.get("dwg_files") == ["rerun.dwg"]
    assert (tmp_path / "originals" / "rerun.dwg").exists()
    assert (tmp_path / "derevitized" / "rerun.dwg").exists()
    assert not (scripts_dir / "old.scr").exists()
    assert not stale_root.exists()
    assert not (tmp_path / "rerun.dwg").exists()


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
                "templates/sheet_script_template.tmpl": "{% for view in viewsOnSheet %}xref path \"{{ view[:-4] }}\" \"./{{ view }}\"\n{% endfor %}",
            }
        ),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    context.environment = env
    stage = ScriptGenerationStage(ScriptGenerator(env), LoggerFactory(settings))
    result = stage.run(context)
    assert result.succeeded is True
    assert (tmp_path / "scripts" / "DWGMAGIC.scr").read_text(encoding="cp1251") == "1"
    sheet_script = (tmp_path / "scripts" / "SHEETA_SHEET.scr").read_text(encoding="cp1251")
    assert 'xref path "SheetA-View-1" "./SheetA-View-1.dwg"' in sheet_script
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
            self.calls = []

        def execute(self, jobs, logger, *, listener=None):
            batch = list(jobs)
            self.calls.append(batch)
            return [
                AutoCadResult(name=job.name, returncode=0, stdout="", stderr="", command=(job.name,))
                for job in batch
            ]

    coordinator = FakeCoordinator()
    stage = AutoCadStage(coordinator, LoggerFactory(settings))
    result = stage.run(context)
    assert result.succeeded is True
    assert [
        [job.name for job in call] for call in coordinator.calls
    ] == [["view:SheetA-View-1"], ["sheet:SheetA"], ["merge"]]
