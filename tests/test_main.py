import main
from dwgmagic.settings import Settings


def test_build_environment_uses_bundled_templates(tmp_path):
    settings = Settings(project_root=tmp_path, tectonica_path=tmp_path / "missing")
    environment = main.build_environment(settings)

    template = environment.get_template("templates/project_script_template.tmpl")
    rendered = template.render(
        tectonica_path=settings.tectonica_path,
        project_name="SampleProject",
        xrefXplodeToggle=True,
        sheetNamesList=[],
        sheets=[],
    )

    assert "SampleProject_MXR.dwg" in rendered
