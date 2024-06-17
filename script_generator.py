from jinja2 import Environment, FileSystemLoader
import os
import config as cfg
from logger import setup_logger

logger = setup_logger("SCRIPT_GENERATOR", log_dir=os.path.join(cfg.paths["dmm"], "logs"))

env = Environment(
    loader=FileSystemLoader(cfg.paths["dmm"]),
    trim_blocks=True,
    lstrip_blocks=True
)

def generate_script(template_name, output_path, **context):
    template = env.get_template(template_name)
    script_content = template.render(context)

    with open(output_path, "w") as script_file:
        script_file.write(script_content)
    logger.info("Generated script %s", output_path)

def generate_project_script(sheet_names_list, xref_xplode_toggle, sheets):
    generate_script('project_script_template.tmpl', './scripts/DWGMAGIC.scr',
                    sheetNamesList=sheet_names_list,
                    tectonica_path=cfg.paths["dmm"],
                    project_name=os.path.basename(os.getcwd()),
                    xrefXplodeToggle=xref_xplode_toggle,
                    sheets=sheets)

def generate_manual_master_merge_script(xref_xplode_toggle, sheets):
    generate_script('mmm_script_template.tmpl', './scripts/MMM.scr',
                    tectonica_path=cfg.paths["dmm"],
                    xrefXplodeToggle=xref_xplode_toggle,
                    sheets=sheets,
                    project_name=os.path.basename(os.getcwd()))

def generate_manual_master_merge_bat(accpath):
    generate_script('manual_merge_bat_template.tmpl', './MANUALMERGE.bat',
                    acc=accpath,
                    project_name=os.path.basename(os.getcwd()))

def generate_sheet_script(sheet_name, views_on_sheet):
    generate_script('sheet_script_template.tmpl', f'./scripts/{sheet_name.upper()}_SHEET.scr',
                    viewsOnSheet=views_on_sheet,
                    tectonica_path=cfg.paths["dmm"],
                    sheetName=sheet_name)

def generate_view_script(view_name):
    generate_script('view_script_template.tmpl', f'./scripts/{view_name.upper()}.scr',
                    viewName=view_name)
