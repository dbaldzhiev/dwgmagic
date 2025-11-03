"""Script generation utilities backed by injected Jinja environment."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from jinja2 import Environment

from dwgmagic.core.context import ProjectContext


@dataclass(slots=True)
class ScriptGenerator:
    environment: Environment

    def generate_all(self, context: ProjectContext, logger) -> Dict[str, Path]:
        project_root = context.project_root
        scripts_dir = project_root / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        dwg_files = context.get("dwg_files", [])
        view_files = [f for f in dwg_files if "-View-" in f]
        sheet_files = [
            f
            for f in dwg_files
            if f.endswith(".dwg") and "-View-" not in f and "-rvt-" not in f
        ]

        sheet_views_lookup = {}
        structured_sheets = []
        for sheet in sheet_files:
            sheet_name = Path(sheet).stem
            views_on_sheet = [view for view in view_files if view.startswith(f"{sheet_name}-View-")]
            sheet_views_lookup[sheet_name] = views_on_sheet
            structured_views = [
                {"viewIndx": Path(view).stem.split("-View-")[-1], "name": Path(view).stem}
                for view in views_on_sheet
            ]
            structured_sheets.append({"sheetName": sheet_name, "viewsOnSheet": structured_views})

        artifacts: Dict[str, Path] = {}
        artifacts["project_script"] = self._render(
            "templates/project_script_template.tmpl",
            scripts_dir / "DWGMAGIC.scr",
            context,
            logger,
            sheetNamesList=sheet_files,
            sheets=structured_sheets,
        )
        artifacts["merge_script"] = self._render(
            "templates/mmm_script_template.tmpl",
            scripts_dir / "MMM.scr",
            context,
            logger,
            sheets=structured_sheets,
        )
        artifacts["merge_bat"] = self._render(
            "templates/manual_merge_bat_template.tmpl",
            project_root / "MANUALMERGE.bat",
            context,
            logger,
        )

        for view in view_files:
            name = Path(view).stem
            artifacts[f"view:{name}"] = self._render(
                "templates/view_script_template.tmpl",
                scripts_dir / f"{name.upper()}.scr",
                context,
                logger,
                viewName=name,
            )

        for sheet in sheet_files:
            name = Path(sheet).stem
            views_on_sheet = sheet_views_lookup.get(name, [])
            artifacts[f"sheet:{name}"] = self._render(
                "templates/sheet_script_template.tmpl",
                scripts_dir / f"{name.upper()}_SHEET.scr",
                context,
                logger,
                sheetName=name,
                viewsOnSheet=views_on_sheet,
            )

        return artifacts

    def _render(self, template_name: str, destination: Path, context: ProjectContext, logger, **kwargs) -> Path:
        template = self.environment.get_template(template_name)
        rendered = template.render(
            tectonica_path=context.settings.tectonica_path,
            project_name=context.project_root.name,
            xrefXplodeToggle=context.settings.xref_xplode_toggle,
            **kwargs,
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="cp1251")
        logger.info("Generated %s", destination)
        return destination


__all__ = ["ScriptGenerator"]

