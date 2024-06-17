import re
import os
import time
import subprocess as sp
import multiprocessing as mp
from threading import Thread

from rich.console import Console
from rich.progress import Progress, track
from rich.tree import Tree
from rich.panel import Panel

import config as cfg
import checks
import logger as lg
import script_generator as sg  # Import the script generator module

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

class Project:
    def __init__(self, log_dir="logs"):
        os.system("")
        self.log_dir = log_dir
        self.project_name = os.path.basename(os.getcwd())
        self.setup()
        self.display_hierarchical_tree()
        self.sheets = self.process_sheets()
        self.generate_scripts()
        self.cleanSheetsExistenceChecker()
        self.run_Project_script()

    def setup(self):
        self.filenames = os.listdir(f"{os.getcwd()}/derevitized/")
        self.accpath = checks.acc_version()
        rgx_str = r"(?!(?:.*-View-\d*)|(?:.*-rvt-))(^.*)(?:\.dwg$)"
        snl = [fname for fname in self.filenames if re.compile(rgx_str).match(fname) is not None]
        snlIndx = [s.replace(".dwg", "") for s in snl]
        self.sheetNamesList = [x for y, x in sorted(zip(snlIndx, snl))]
        self.xrefXplodeToggle = True

    def display_hierarchical_tree(self):
        tree = Tree(f" [bold blue]{self.project_name}[/bold blue]", guide_style="bold bright_blue")
        for sheet_name in self.sheetNamesList:
            sheet_branch = tree.add(f" [green]{sheet_name.replace('.dwg', '')}[/green]")
            view_names_on_sheet = list(filter(re.compile(f"{sheet_name.replace('.dwg', '')}-View-\\d+").match, self.filenames))
            for view_name in view_names_on_sheet:
                sheet_branch.add(f" [yellow]{view_name.replace('.dwg', '')}[/yellow]")
        console.print(tree)

    def process_sheets(self):
        if cfg.sheetThreading:
            try:
                with mp.Pool(mp.cpu_count()) as pool:
                    return pool.map(Sheet, [(s, self) for s in self.sheetNamesList])
            except Exception as e:
                console.print(f"Error processing sheets: {str(e)}", style="bold red")
                return []
        else:
            return [Sheet((s, self)) for s in self.sheetNamesList]

    def generate_scripts(self):
        sg.generate_project_script(self.sheetNamesList, self.xrefXplodeToggle, self.sheets)
        sg.generate_manual_master_merge_script(self.xrefXplodeToggle, self.sheets)
        sg.generate_manual_master_merge_bat(self.accpath)

    def cleanSheetsExistenceChecker(self):
        timeout = time.time() + cfg.deadline
        while True:
            existence = [(s, os.path.isfile(s.cleanSheetFilePath)) for s in self.sheets]
            if all(ex[1] for ex in existence) or time.time() > timeout:
                log_and_print("All sheets derevitazation confirmed!", style="bold green")
                if cfg.verbose:
                    log_and_print("\n".join([f"{s.cleanSheetFilePath} is {ex}" for s, ex in existence]), None)
                break
            else:
                if cfg.verbose:
                    log_and_print(f"Time left: {timeout - time.time()}", None)
                    log_and_print("\n".join([f"{s.cleanSheetFilePath} is {ex}" for s, ex in existence]), None)
                    time.sleep(1)

    def run_Project_script(self):
        mmlg = lg.setup_logger("MAIN_MERGER", log_dir=self.log_dir)
        command = [
            self.accpath,
            "/s",
            f"{os.getcwd()}/scripts/DWGMAGIC.scr"
        ]
        log_and_print(f"Running Command: {' '.join(command)}", mmlg, style="bold yellow")

        with open("./scripts/DWGMAGIC.scr", "r") as file:
            script_lines = file.readlines()
        
        total_commands = sum(1 for line in script_lines if line.strip())

        process = sp.Popen(command, stdout=sp.PIPE, shell=True, encoding='utf-16-le', errors='replace')
        
        command_pattern = re.compile(r'^Command: (.+)$')
        executed_commands = 0

        with Progress() as progress:
            task = progress.add_task("Processing", total=total_commands)
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    match = command_pattern.match(output.strip())
                    if match:
                        executed_commands += 1
                        progress.update(task, advance=1)
            
            progress.update(task, completed=total_commands)

        try:
            os.remove(f"{os.path.basename(os.getcwd())}_MM.bak")
        except:
            pass
        log_and_print("DWG MAGIC COMPLETE", mmlg, style="bold green")

class Sheet:
    def __init__(self, args):
        sn, project = args
        self.acc = project.accpath
        self.sheetName = sn.replace(".dwg", "")
        self.workingFile = sn
        self.sheetCleanerScript = f"{self.sheetName.upper()}_SHEET.scr"
        self.viewNamesOnSheetList = list(filter(re.compile(f"{self.sheetName}-View-\\d+").match, project.filenames))

        self.viewsOnSheet = self.process_views(project)

        sg.generate_sheet_script(self.sheetName, self.viewsOnSheet)
        self.run_Sheet_cleaner()
        self.cleanSheetFilePath = f"{os.getcwd()}/derevitized/{self.sheetName}_xrefed.dwg"
    
    def process_views(self, project):
        views = []
        try:
            if cfg.viewThreading:
                threads = []
                for view in self.viewNamesOnSheetList:
                    thread = Thread(target=lambda v: views.append(View((v, project))), args=(view,))
                    thread.start()
                    threads.append(thread)
                for thread in threads:
                    thread.join()
            else:
                for view in track(self.viewNamesOnSheetList, description=f"Processing Views for Sheet {self.sheetName}"):
                    views.append(View((view, project)))
        except Exception as e:
            console.print(f"Error processing views for sheet {self.sheetName}: {str(e)}", style="bold red")
        return views
    
    def run_Sheet_cleaner(self):
        slg = lg.setup_logger(f"SHEET_{self.sheetName}")
        command = [
            self.acc,
            "/i",
            f"{os.getcwd()}/derevitized/{self.sheetName}.dwg",
            "/s",
            f"{os.getcwd()}/scripts/{self.sheetCleanerScript}"
        ]
        log_and_print(f"Cleaning Sheet {self.sheetName} with Script {self.sheetCleanerScript}", slg, style="bold yellow")

        output, err = run_command(command, log=slg, verbose=cfg.verbose)
        if output is None:
            slg.error(f"Failed to clean sheet {self.sheetName}: {str(err)}")
        else:
            try:
                os.remove(f"{os.getcwd()}/derevitized/{self.workingFile}")
            except Exception as e:
                slg.error(f"Failed to remove file {self.workingFile}: {str(e)}")

class View:
    def __init__(self, args):
        vn, project = args
        self.acc = project.accpath
        self.viewName = vn.replace(".dwg", "")
        self.viewIndx = re.compile(r"\d+-View-(\d+).dwg").search(vn).group(1)
        self.parentSheetIndx = re.compile(r"(\d+)-View-\d+.dwg").search(vn).group(1)
        self.viewCleanerScript = f"{self.viewName.upper()}.scr"
        
        sg.generate_view_script(self.viewName)
        self.run_View_cleaner()

    def run_View_cleaner(self):
        vlg = lg.setup_logger(f"VIEW_{self.viewName}")
        command = [
            self.acc,
            "/i",
            f"{os.getcwd()}/derevitized/{self.viewName}.dwg",
            "/s",
            f"{os.getcwd()}/scripts/{self.viewCleanerScript}"
        ]
        vlg.debug(f"Cleaning View {self.viewName} with Script {self.viewCleanerScript}")

        log_and_print(f"Cleaning View {self.viewName} with Script {self.viewCleanerScript}", vlg, style="bold yellow")

        output, err = run_command(command, log=vlg, verbose=cfg.verbose)
        if output is None:
            vlg.error(f"Failed to clean view {self.viewName}: {str(err)}")
