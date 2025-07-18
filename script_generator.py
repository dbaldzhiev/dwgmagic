# script_generator.py
from jinja2 import Environment, FileSystemLoader
import os
import config as cfg
from logger import setup_logger

# Initialize the Jinja2 environment globally
env = Environment(
    loader=FileSystemLoader(cfg.DMM_PATH),
    trim_blocks=True,
    lstrip_blocks=True
)

def setup_script_logger(log_dir=None):
    log_dir = log_dir or os.path.join(cfg.DMM_PATH, "logs")
    return setup_logger("SCRIPT_GENERATOR", log_dir=log_dir)

def generate_script(template_name, output_path, logger, **context):
    template = env.get_template(template_name)
    script_content = template.render(context)
    with open(output_path, "w") as script_file:
        script_file.write(script_content)
    logger.info("Generated script %s", output_path)

def generate_project_script(sheet_names_list, xref_xplode_toggle, sheets, log_dir=None):
    logger = setup_script_logger(log_dir)
    generate_script('./templates/project_script_template.tmpl', './scripts/DWGMAGIC.scr', logger,
                    sheetNamesList=sheet_names_list,
                    tectonica_path=cfg.DMM_PATH,
                    project_name=os.path.basename(os.getcwd()),
                    xrefXplodeToggle=xref_xplode_toggle,
                    sheets=sheets)

def generate_manual_master_merge_script(xref_xplode_toggle, sheets, log_dir=None):
    logger = setup_script_logger(log_dir)
    generate_script('./templates/mmm_script_template.tmpl', './scripts/MMM.scr', logger,
                    tectonica_path=cfg.DMM_PATH,
                    xrefXplodeToggle=xref_xplode_toggle,
                    sheets=sheets,
                    project_name=os.path.basename(os.getcwd()))

def generate_manual_master_merge_bat(accpath, log_dir=None):
    logger = setup_script_logger(log_dir)
    generate_script('./templates/manual_merge_bat_template.tmpl', './MANUALMERGE.bat', logger,
                    acc=accpath,
                    project_name=os.path.basename(os.getcwd()))

def generate_sheet_script(sheet_name, views_on_sheet,sheet_cleaner_script, log_dir=None):
    logger = setup_script_logger(log_dir)
    generate_script('./templates/sheet_script_template.tmpl', f'./scripts/{sheet_cleaner_script}', logger,
                    viewsOnSheet=views_on_sheet,
                    tectonica_path=cfg.DMM_PATH,
                    sheetName=sheet_name)

def generate_view_script(view_name,view_cleaner_script, log_dir=None):
    logger = setup_script_logger(log_dir)
    generate_script('./templates/view_script_template.tmpl', f'./scripts/{view_cleaner_script}', logger,
                    viewName=view_name)
