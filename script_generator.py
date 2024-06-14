from jinja2 import Environment, FileSystemLoader
import os
import config as cfg

def generate_Project_Script(sheetNamesList, xrefXplodeToggle, sheets):
    env = Environment(
        loader=FileSystemLoader(cfg.paths["dmm"]),
        trim_blocks=True,
        lstrip_blocks=True
    )
    template = env.get_template('project_script_template.tmpl')
    
    script_content = template.render(
        sheetNamesList=sheetNamesList,
        tectonica_path=cfg.paths["dmm"],
        project_name=os.path.basename(os.getcwd()),
        xrefXplodeToggle=xrefXplodeToggle,
        sheets=sheets
    )

    with open("./scripts/DWGMAGIC.scr", "w") as script_file:
        script_file.write(script_content)

def generate_Manual_Master_Merge_Script(xrefXplodeToggle, sheets):
    env = Environment(
        loader=FileSystemLoader(cfg.paths["dmm"]),
        trim_blocks=True,
        lstrip_blocks=True
    )
    template = env.get_template('mmm_script_template.tmpl')
    
    script_content = template.render(
        tectonica_path=cfg.paths["dmm"],
        xrefXplodeToggle=xrefXplodeToggle,
        sheets=sheets,
        project_name=os.path.basename(os.getcwd())
    )

    with open("./scripts/MMM.scr", "w") as script_file:
        script_file.write(script_content)

def generate_Manual_Master_Merge_bat(accpath):
    env = Environment(
        loader=FileSystemLoader(cfg.paths["dmm"]),
        trim_blocks=True,
        lstrip_blocks=True
    )
    template = env.get_template('manual_merge_bat_template.tmpl')
    
    bat_content = template.render(
        acc=accpath,
        project_name=os.path.basename(os.getcwd())
    )

    with open("./MANUALMERGE.bat", "w") as bat_file:
        bat_file.write(bat_content)

def generate_Sheet_script(sheetName, viewsOnSheet):
    env = Environment(
        loader=FileSystemLoader(cfg.paths["dmm"]),
        trim_blocks=True,
        lstrip_blocks=True
    )
    template = env.get_template('sheet_script_template.tmpl')
    
    script_content = template.render(
        viewsOnSheet=viewsOnSheet,
        tectonica_path=cfg.paths["dmm"],
        sheetName=sheetName
    )

    with open(f"./scripts/{sheetName.upper()}_SHEET.scr", "w") as script_file:
        script_file.write(script_content)

def generate_View_script(viewName):
    env = Environment(
        loader=FileSystemLoader(cfg.paths["dmm"]),
        trim_blocks=True,
        lstrip_blocks=True
    )
    template = env.get_template('view_script_template.tmpl')
    
    script_content = template.render(
        viewName=viewName
    )

    with open(f"./scripts/{viewName.upper()}.scr", "w") as script_file:
        script_file.write(script_content)
