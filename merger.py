from rich.console import Console
from rich.progress import Progress, Live, track
from rich.tree import Tree
import joblib as jb
import re
import os
import time
import shlex
import subprocess as sp
from jinja2 import Environment, FileSystemLoader
import config as cfg
import checks
import logger as lg
import script_generator as sg  # Import the script generator module


console = Console()

#The general PROJECT CLASS
class Project:
    def __init__(self):
        os.system("")
        self.setup()
        sg.generate_Project_Script(self.sheetNamesList, self.xrefXplodeToggle, self.sheets)  # Use function from script_generator
        sg.generate_Manual_Master_Merge_Script(self.xrefXplodeToggle, self.sheets)  # Use function from script_generator
        sg.generate_Manual_Master_Merge_bat(self.accpath)  # Use function from script_generator
        self.cleanSheetsExistenceChecker()
        self.run_Project_script()

    def setup(self):
        self.filenames = os.listdir("{0}/derevitized/".format(os.getcwd()))
        self.accpath = checks.accVersion()
        rgx_str = r"(?!(?:.*-View-\d*)|(?:.*-rvt-))(^.*)(?:\.dwg$)"
        snl = [fname for fname in self.filenames if re.compile(rgx_str).match(fname) is not None]
        snlIndx = [s.replace(".dwg", "") for s in snl]
        self.sheetNamesList = [x for y, x in sorted(zip(snlIndx, snl))]
        self.xrefXplodeToggle = True
        if cfg.sheetThreading:
            self.sheets = jb.Parallel(n_jobs=-1, batch_size=1)(
                jb.delayed(Sheet)(s, self) for s in self.sheetNamesList)
        else:
            self.sheets = [Sheet(s, self) for s in self.sheetNamesList]
    
    def cleanSheetsExistenceChecker(self):
        timeout = time.time() + cfg.deadline
        while True:
            existance = list(zip(self.sheets, [os.path.isfile(s.cleanSheetFilePath) for s in self.sheets]))
            if all([ex for sh, ex in existance]) or time.time() > timeout:
                console.print("All sheets derevitazation confirmed!", style="bold green")
                if cfg.verbose:
                    print("\n".join(["{0} is {1}".format(e[0].cleanSheetFilePath, e[1]) for e in existance]))
                break
            else:
                if cfg.verbose:
                    print("Time left: {0}".format(timeout - time.time()))
                    print("\n".join(["{0} is {1}".format(e[0].cleanSheetFilePath, e[1]) for e in existance]))
                    time.sleep(1)
                    
    def run_Project_script(self):
        mmlg = lg.newLog("MAIN_MERGER")
        command = "\"{acc}\" /s \"{path}/scripts/DWGMAGIC.scr\"".format(acc=self.accpath, path=os.getcwd())
        console.print(f"Running: {command}", style="bold yellow")
        mmlg.debug(f"Running: {command}")

        # Read the DWGMAGIC.scr file to count the total number of commands
        with open("./scripts/DWGMAGIC.scr", "r") as file:
            script_lines = file.readlines()
        
        total_commands = sum(1 for line in script_lines if line.strip())

        process = sp.Popen(shlex.split(command), stdout=sp.PIPE, shell=True, encoding='utf-16-le', errors='replace')

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
        mmlg.debug("DWG MAGIC COMPLETE")
        console.print("DWG MAGIC COMPLETE", style="bold green")

class Sheet:
    def __init__(self, sn, project):
        self.acc = project.accpath
        self.sheetName = sn.replace(".dwg", "")
        self.workingFile = sn
        self.sheetCleanerScript = f"{self.sheetName.upper()}_SHEET.scr"
        self.viewNamesOnSheetList = list(filter(re.compile(f"{self.sheetName}-View-\\d+").match, project.filenames))

        #console.print(f"Processing Sheet: {self.sheetName} -> Views: {self.viewNamesOnSheetList}", style="bold blue")

        self.viewsOnSheet = self.process_views(project)

        sg.generate_Sheet_script(self.sheetName, self.viewsOnSheet)  # Use function from script_generator
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
        command = f"{self.acc} /i \"{os.getcwd()}/derevitized/{self.sheetName}.dwg\" /s \"{os.getcwd()}/scripts/{self.sheetCleanerScript}\""
        if cfg.verbose:
            console.print(f"Cleaning Sheet {self.sheetName} with Script {self.sheetCleanerScript}", style="bold yellow")
            console.print(f"Command: {command}", style="yellow")

        try:
            process = sp.Popen(command, stdout=sp.PIPE, encoding='utf-16-le', errors='replace')
            output, err = process.communicate()
            slg.debug(f"Cleaning Sheet {self.sheetName} with Script {self.sheetCleanerScript}")
            slg.debug(output)
        except Exception as e:
            slg.error(f"Failed to clean sheet {self.sheetName}: {str(e)}")
        finally:
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
        
        #console.print(f"Processing View: {self.viewName}", style="bold blue")

        self.xrefs = self.get_xrefs_from_view()
        sg.generate_View_script(self.viewName)  # Use function from script_generator
        self.run_View_cleaner()

    def get_xrefs_from_view(self):
        command = f"{self.acc} /s {os.getcwd()}/scripts/CHECKER.scr /i {os.getcwd()}/derevitized/{self.viewName}.dwg"
        xrefs = []
        try:
            process = sp.Popen(command, stdout=sp.PIPE, encoding='utf-16-le', errors='replace')
            output, err = process.communicate()
            xrefsRegex = re.compile(r"\"(.*)\" loaded: (.*)")
            xrefs = xrefsRegex.findall(output)
            if cfg.verbose:
                console.print(f"View {self.viewName} has the following XREFS: {xrefs}", style="yellow")
        except Exception as e:
            console.print(f"Error getting xrefs for view {self.viewName}: {str(e)}", style="bold red")
        return [Xref(name, path) for name, path in xrefs]

    def run_View_cleaner(self):
        vlg = lg.newLog(f"VIEW_{self.viewName}")
        command = f"{self.acc} /i \"{os.getcwd()}/derevitized/{self.viewName}.dwg\" /s \"{os.getcwd()}/scripts/{self.viewCleanerScript}\""
        vlg.debug(f"Cleaning View {self.viewName} with Script {self.viewCleanerScript}")

        if cfg.verbose:
            console.print(f"Cleaning View {self.viewName} with Script {self.viewCleanerScript}", style="bold yellow")
            console.print(f"Command: {command}", style="yellow")

        try:
            process = sp.Popen(command, stdout=sp.PIPE, encoding='utf-16-le', errors='replace')
            output, err = process.communicate()
            vlg.debug(output)
        except Exception as e:
            vlg.error(f"Failed to clean view {self.viewName}: {str(e)}")


class Xref:
    def __init__(self, name, path):
        self.xrefName = name
        self.xrefPath = path
