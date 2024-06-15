from rich.console import Console
from rich.progress import Progress, Live, track
from rich.tree import Tree
import joblib as jb
import re
import os
import time
import subprocess as sp
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
    def __init__(self):
        os.system("")
        self.setup()
        self.generate_scripts()
        self.cleanSheetsExistenceChecker()
        self.run_Project_script()

    def setup(self):
        self.filenames = os.listdir(f"{os.getcwd()}/derevitized/")
        self.accpath = checks.accVersion()
        rgx_str = r"(?!(?:.*-View-\d*)|(?:.*-rvt-))(^.*)(?:\.dwg$)"
        snl = [fname for fname in self.filenames if re.compile(rgx_str).match(fname) is not None]
        snlIndx = [s.replace(".dwg", "") for s in snl]
        self.sheetNamesList = [x for y, x in sorted(zip(snlIndx, snl))]
        self.xrefXplodeToggle = True
        self.sheets = self.process_sheets()

    def generate_scripts(self):
        sg.generate_Project_Script(self.sheetNamesList, self.xrefXplodeToggle, self.sheets)
        sg.generate_Manual_Master_Merge_Script(self.xrefXplodeToggle, self.sheets)
        sg.generate_Manual_Master_Merge_bat(self.accpath)

    def process_sheets(self):
        if cfg.sheetThreading:
            try:
                return jb.Parallel(n_jobs=-1, batch_size=1)(
                    jb.delayed(Sheet)(s, self) for s in self.sheetNamesList)
            except Exception as e:
                console.print(f"Error processing sheets: {str(e)}", style="bold red")
                return []
        else:
            return [Sheet(s, self) for s in self.sheetNamesList]

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
        mmlg = lg.newLog("MAIN_MERGER")
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
    def __init__(self, sn, project):
        self.acc = project.accpath
        self.sheetName = sn.replace(".dwg", "")
        self.workingFile = sn
        self.sheetCleanerScript = f"{self.sheetName.upper()}_SHEET.scr"
        self.viewNamesOnSheetList = list(filter(re.compile(f"{self.sheetName}-View-\\d+").match, project.filenames))

        self.viewsOnSheet = self.process_views(project)

        sg.generate_Sheet_script(self.sheetName, self.viewsOnSheet)
        self.run_Sheet_cleaner()
        self.cleanSheetFilePath = f"{os.getcwd()}/derevitized/{self.sheetName}_xrefed.dwg"
    
    def process_views(self, project):
        views = []
        try:
            if cfg.viewThreading:
                views = jb.Parallel(n_jobs=-1, batch_size=1)(
                    jb.delayed(View)(v, project) for v in self.viewNamesOnSheetList
                )
            else:
                for view in track(self.viewNamesOnSheetList, description=f"Processing Views for Sheet {self.sheetName}"):
                    views.append(View(view, project))
        except Exception as e:
            console.print(f"Error processing views for sheet {self.sheetName}: {str(e)}", style="bold red")
        return views
    
    def run_Sheet_cleaner(self):
        slg = lg.newLog(f"SHEET_{self.sheetName}")
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
    def __init__(self, vn, project):
        self.acc = project.accpath
        self.viewName = vn.replace(".dwg", "")
        self.viewIndx = re.compile(r"\d+-View-(\d+).dwg").search(vn).group(1)
        self.parentSheetIndx = re.compile(r"(\d+)-View-\d+.dwg").search(vn).group(1)
        self.viewCleanerScript = f"{self.viewName.upper()}.scr"
        
        sg.generate_View_script(self.viewName)
        self.run_View_cleaner()

    def run_View_cleaner(self):
        vlg = lg.newLog(f"VIEW_{self.viewName}")
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
