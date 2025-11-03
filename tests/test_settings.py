from pathlib import Path

from dwgmagic.settings import load_settings


def test_load_settings_precedence(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text("""
log_level = "INFO"
log_dir = "from_config"
template_roots = ["CONFIG_ROOT"]
""")

    cli_template = tmp_path / "cli_templates"
    env = {
        "DWGMAGIC_LOG_LEVEL": "WARNING",
        "DWGMAGIC_TEMPLATE_ROOT": str(tmp_path / "env_templates"),
        "DWGMAGIC_VERBOSE": "1",
    }

    settings = load_settings(
        tmp_path,
        config_file=config,
        template_roots=[cli_template],
        autocad_path=tmp_path / "cli_acc.exe",
        env=env,
    )

    assert settings.log_level == "WARNING"
    assert settings.log_dir == Path("from_config")
    assert settings.verbose is True
    assert settings.autocad_executable == tmp_path / "cli_acc.exe"
    assert settings.template_roots == (cli_template,)


def test_resolve_template_roots_defaults(tmp_path):
    settings = load_settings(tmp_path)
    roots = settings.resolve_template_roots()
    assert settings.tectonica_path in roots
    assert tmp_path in roots
