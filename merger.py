import re
import os
import subprocess as sp
import multiprocessing as mp
from rich.console import Console
from rich.progress import Progress
from rich.tree import Tree
import config as cfg
import checks
import logger as lg
import script_generator as sg

console = Console()

def run_command(command, log=None, verbose=False):
    if verbose:
        log_and_print(f"Running Command: {' '.join(command)}", log, style="bold yellow")
    try:
        process = sp.Popen(command, stdout=sp.PIPE, shell=True, encoding='utf-16-le', errors='replace')
        output, err = process.communicate()
        if log:
            log.debug(output)
        return output, err
    except Exception as e:
        log_and_print(f"Failed to run command {command}: {str(e)}", log, style="bold red")
        return None, e

def log_and_print(message, log=None, style=None):
    if log:
        log.debug(message)
    if cfg.verbose:
        console.print(message, style=style)

def view_worker(view, acc_path, log_dir):
    view_name = view.replace(".dwg", "")
    view_cleaner_script = f"{view_name.upper()}.scr"
    sg.generate_view_script(view_name, view_cleaner_script, log_dir=log_dir)

    view_logger = lg.setup_logger(f"{view_name.upper()}", log_dir=log_dir)
    command = [
        acc_path,
        "/i",
        f"{os.getcwd()}/derevitized/{view}",
        "/s",
        f"{os.getcwd()}/scripts/{view_cleaner_script}"
    ]
    log_and_print(f"Cleaning View {view_name} with Script {view_cleaner_script}", view_logger, style="bold yellow")
    output, err = run_command(command, log=view_logger, verbose=cfg.verbose)
    if output is None:
        view_logger.error(f"Failed to clean view {view_name}: {str(err)}")

def sheet_worker(sheet, acc_path, log_dir, files):
    sheet_name = sheet.replace(".dwg", "")
    views_on_sheet = list(filter(re.compile(f"{sheet_name}-View-\\d+").match, files))
    sheet_cleaner_script = f"{sheet_name.upper()}_SHEET.scr"
    sg.generate_sheet_script(sheet_name, views_on_sheet, sheet_cleaner_script, log_dir=log_dir)

    sheet_logger = lg.setup_logger(f"SHEET_{sheet_name}", log_dir=log_dir)
    command = [
        acc_path,
        "/i",
        f"{os.getcwd()}/derevitized/{sheet}",
        "/s",
        f"{os.getcwd()}/scripts/{sheet_cleaner_script}"
    ]
    log_and_print(f"Cleaning Sheet {sheet_name} with Script {sheet_cleaner_script}", sheet_logger, style="bold yellow")
    output, err = run_command(command, log=sheet_logger, verbose=cfg.verbose)
    if output is None:
        sheet_logger.error(f"Failed to clean sheet {sheet_name}: {str(err)}")
    else:
        try:
            os.remove(f"{os.getcwd()}/derevitized/{sheet}")
        except Exception as e:
            sheet_logger.error(f"Failed to remove file {sheet}: {str(e)}")

class Project:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        self.project_name = os.path.basename(os.getcwd())
        self.setup_environment()
        #self.display_hierarchy()
        self.generate_scripts()
        self.process_views()
        self.process_sheets()
        self.merge_results()

    def setup_environment(self):
        self.files = os.listdir(f"{os.getcwd()}/derevitized/")
        self.acc_path = checks.acc_version()
        self.sheet = sorted([sheet for sheet in self.files if re.match(r"(?!(?:.*-View-\d*)|(?:.*-rvt-))(^.*)(?:\.dwg$)", sheet)])
        self.view = [view for view in self.files if re.match(r".*-View-\d+\.dwg$", view)]
        self.xref_xplode_toggle = True

    def display_hierarchy(self):
        tree = Tree(f" [bold orange1]{self.project_name}[/bold orange1]", guide_style="bold orange1")
        for sheet in self.sheet:
            sheet_branch = tree.add(f" [wheat1]{sheet}[/wheat1]")
            views_on_sheet = list(filter(re.compile(f"{sheet.replace('.dwg', '')}-View-\\d+").match, self.files))
            for view in views_on_sheet:
                view_branch = sheet_branch.add(f" [sky_blue2]{view}[/sky_blue2]")
                view_number = re.search(f"{sheet.replace('.dwg','')}-View-(.+).dwg", view).group(1)
                xrefs_in_view = list(filter(re.compile(f"{sheet.replace('.dwg','')}-.*-rvt-{view_number}.*.dwg").match, self.files))
                for xref in xrefs_in_view:
                    view_branch.add(f" [blue]{xref}[/blue]")
        console.print(tree)

    def generate_scripts(self):
        sg.generate_project_script(self.sheet, self.xref_xplode_toggle, [], log_dir=self.log_dir)
        sg.generate_manual_master_merge_script(self.xref_xplode_toggle, [], log_dir=self.log_dir)
        sg.generate_manual_master_merge_bat(self.acc_path, log_dir=self.log_dir)

    def process_views(self):
        with mp.Pool(mp.cpu_count()) as pool, Progress() as progress:
            task = progress.add_task("Processing Views", total=len(self.view))
            def update_progress(result):
                progress.update(task, advance=1)
            for view in self.view:
                pool.apply_async(view_worker, args=(view, self.acc_path, self.log_dir), callback=update_progress)
            pool.close()
            pool.join()

    def process_sheets(self):
        with mp.Pool(mp.cpu_count()) as pool, Progress() as progress:
            task = progress.add_task("Processing Sheets", total=len(self.sheet))
            def update_progress(result):
                progress.update(task, advance=1)
            for sheet in self.sheet:
                pool.apply_async(sheet_worker, args=(sheet, self.acc_path, self.log_dir, self.files), callback=update_progress)
            pool.close()
            pool.join()

    def merge_results(self):
        main_logger = lg.setup_logger("MAIN_MERGER", log_dir=self.log_dir)
        command = [
            self.acc_path,
            "/s",
            f"{os.getcwd()}/scripts/DWGMAGIC.scr"
        ]
        log_and_print(f"Running Command: {' '.join(command)}", main_logger, style="bold yellow")

        with open("./scripts/DWGMAGIC.scr", "r") as file:
            script_lines = file.readlines()

        commands = [line for line in script_lines if line.strip()]
        total_commands = len(commands)
        process = sp.Popen(command, stdout=sp.PIPE, shell=True, encoding='utf-16-le', errors='replace')


        with Progress() as progress:
            task = progress.add_task("Processing the Merge", total=total_commands)
            while True:
                output = process.stdout.readline()
                log_and_print(f"{output.strip()}", main_logger, style="bold yellow")
                if output == '' and process.poll() is not None:
                    break
                if output and len(commands)>0:
                    match = re.compile(commands[0].split()[0]).search(output.strip())
                    if match:
                        del commands[0]
                        progress.update(task, advance=1)
            progress.update(task, completed=total_commands)

        try:
            os.remove(f"{os.path.basename(os.getcwd())}_MM.bak")
        except:
            pass
        log_and_print("DWG MAGIC COMPLETE", main_logger, style="bold green")

if __name__ == "__main__":
    Project()
