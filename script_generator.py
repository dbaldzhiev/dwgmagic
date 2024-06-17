from jinja2 import Environment, FileSystemLoader
import os
import config as cfg
from logger import setup_logger

# Initialize the Jinja2 environment globally
env = Environment(
    loader=FileSystemLoader(cfg.paths["dmm"]),
    trim_blocks=True,
    lstrip_blocks=True
)

def setup_script_logger(log_dir=None):
    if log_dir is None:
        log_dir = os.path.join(cfg.paths["dmm"], "logs")
    return setup_logger("SCRIPT_GENERATOR", log_dir=log_dir)

def generate_script(template_name, output_path, logger, **context):
    template = env.get_template(template_name)
    script_content = template.render(context)

    with open(output_path, "w") as script_file:
        script_file.write(script_content)
    logger.info("Generated script %s", output_path)

def generate_project_script(sheet_names_list, xref_xplode_toggle, sheets, log_dir=None):
    logger = setup_script_logger(log_dir)
    generate_script('project_script_template.tmpl', './scripts/DWGMAGIC.scr', logger,
                    sheetNamesList=sheet_names_list,
                    tectonica_path=cfg.paths["dmm"],
                    project_name=os.path.basename(os.getcwd()),
                    xrefXplodeToggle=xref_xplode_toggle,
                    sheets=sheets)

def generate_manual_master_merge_script(xref_xplode_toggle, sheets, log_dir=None):
    logger = setup_script_logger(log_dir)
    generate_script('mmm_script_template.tmpl', './scripts/MMM.scr', logger,
                    tectonica_path=cfg.paths["dmm"],
                    xrefXplodeToggle=xref_xplode_toggle,
                    sheets=sheets,
                    project_name=os.path.basename(os.getcwd()))

def generate_manual_master_merge_bat(accpath, log_dir=None):
    logger = setup_script_logger(log_dir)
    generate_script('manual_merge_bat_template.tmpl', './MANUALMERGE.bat', logger,
                    acc=accpath,
                    project_name=os.path.basename(os.getcwd()))

def generate_sheet_script(sheet_name, views_on_sheet, log_dir=None):
    logger = setup_script_logger(log_dir)
    generate_script('sheet_script_template.tmpl', f'./scripts/{sheet_name.upper()}_SHEET.scr', logger,
                    viewsOnSheet=views_on_sheet,
                    tectonica_path=cfg.paths["dmm"],
                    sheetName=sheet_name)

def generate_view_script(view_name, log_dir=None):
    logger = setup_script_logger(log_dir)
    generate_script('view_script_template.tmpl', f'./scripts/{view_name.upper()}.scr', logger,
                    viewName=view_name)
