import os
import re
import shlex
import subprocess as sp
import sys
import time
from threading import Timer
import joblib as jb
from tqdm import tqdm
import logging
from rich.console import Console
from rich.progress import track
from jinja2 import Template, Environment, FileSystemLoader
import config as cfg
import checks
import logger as lg

console = Console()

#The general PROJECT CLASS
class Project:
    def __init__(self):
        os.system("")
        self.setup()
        self.generate_Project_Script()
        self.generate_Manual_Master_Merge_Script()
        self.generate_Manual_Master_Merge_bat()
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
        if cfg.threaded:
            self.sheets = jb.Parallel(n_jobs=-1, batch_size=1, verbose=100)(
                jb.delayed(Sheet)(s, self) for s in self.sheetNamesList)
        else:
            self.sheets = [Sheet(s, self) for s in self.sheetNamesList]
    
    #The scrtipt that attaches all xrefs and explodes them saves MASTERMERGED.DWG
    def generate_Project_Script(self):
        env = Environment(
            loader=FileSystemLoader(cfg.paths["dmm"]),
            trim_blocks=True,
            lstrip_blocks=True
        )
        template = env.get_template('project_script_template.tmpl')
        
        script_content = template.render(
            sheetNamesList=self.sheetNamesList,
            tectonica_path=cfg.paths["dmm"],
            project_name=os.path.basename(os.getcwd()),
            xrefXplodeToggle=self.xrefXplodeToggle,
            sheets=self.sheets
        )

        with open("./scripts/DWGMAGIC.scr", "w") as script_file:
            script_file.write(script_content)

    #Making MANUAL master merge script
    def generate_Manual_Master_Merge_Script(self):
        scr = open("./scripts/MMM.scr", "w+")
        scr.write("netload {0}/tectonica.dll\n".format(cfg.paths["dmm"]))
        scr.write("visretain 0\n")
        scr.write("xbind d *\n")
        scr.write("xbind s *\n")
        scr.write("xbind lt *\n")
        if self.xrefXplodeToggle:
            scr.write("tecbxt\n")
        if not self.xrefXplodeToggle:
            scr.write("bindtype 1\n")
            scr.write("xref bind *\n")
            scr.write("xplode all\n")
            scr.write("\n")
            scr.write("g\n")
            scr.write("\n")
            scr.write("(load(findfile \"ssx.lsp\"))\n")
            for sheet in self.sheets:
                for view in sheet.viewsOnSheet:
                    scr.write("ssx\n")
                    scr.write("\n")
                    scr.write("block\n")
                    scr.write("{0}-View-{1}\n".format(str(sheet.sheetName), view.viewIndx))
                    scr.write("\n")
                    scr.write("xplode p\n")
                    scr.write("\n")
                    scr.write("\n")
        scr.write("-purge all * n\n")
        scr.write("audit y\n")
        scr.write("zoom all\n")
        scr.write("saveas\n")
        scr.write("2007\n")
        scr.write("\"./{0}_MMM.dwg\"\n".format(os.path.basename(os.getcwd())))
        scr.write("filedia 1\n")
        scr.write("qsave\n")
        scr.close()

    #Making the bat file that uses manual master merge script
    def generate_Manual_Master_Merge_bat(self):
        scr = open("./MANUALMERGE.bat", "w+")
        scr.write("pushd %~d1%~p1\n")
        scr.write("\"{acc}\" /i \"%cd%/{n}_MXR.dwg\" /s \"%cd%/scripts/MMM.scr\"\n".format(acc=self.accpath,
                                                                                           n=os.path.basename(
                                                                                               os.getcwd())))
        scr.write("popd\n")
        scr.write("pause\n")
    
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
        process = sp.Popen(shlex.split(command), stdout=sp.PIPE, shell=True, encoding='utf-16-le', errors='replace')

        for line in track(process.stdout, description="Processing"):
            console.print(line[:100] + ".." if len(line) > 100 else line.strip("\n"))
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

        console.print(f"Processing Sheet: {self.sheetName} -> Views: {self.viewNamesOnSheetList}", style="bold blue")

        self.viewsOnSheet = self.process_views(project)

        self.generate_Sheet_script()
        self.run_Sheet_cleaner()
        self.cleanSheetFilePath = f"{os.getcwd()}/derevitized/{self.sheetName}_xrefed.dwg"
    
    def process_views(self, project):
        views = []
        try:
            if cfg.threaded:
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
            
    def generate_Sheet_script(self):
        env = Environment(
            loader=FileSystemLoader(cfg.paths["dmm"]),
            trim_blocks=True,
            lstrip_blocks=True
        )
        template = env.get_template('sheet_script_template.tmpl')
        
        script_content = template.render(
            viewsOnSheet=self.viewsOnSheet,
            tectonica_path=cfg.paths["dmm"],
            sheetName=self.sheetName
        )

        with open(f"./scripts/{self.sheetCleanerScript}", "w") as script_file:
            script_file.write(script_content)

class View:
    def __init__(self, vn, project):
        self.acc = project.accpath
        self.viewName = vn.replace(".dwg", "")
        self.viewIndx = re.compile(r"\d+-View-(\d+).dwg").search(vn).group(1)
        self.parentSheetIndx = re.compile(r"(\d+)-View-\d+.dwg").search(vn).group(1)
        self.viewCleanerScript = f"{self.viewName.upper()}.scr"
        
        console.print(f"Processing View: {self.viewName}", style="bold blue")

        self.xrefs = self.get_xrefs_from_view()
        self.generate_View_script()
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

    def generate_View_script(self):
        env = Environment(
            loader=FileSystemLoader(cfg.paths["dmm"]),
            trim_blocks=True,
            lstrip_blocks=True
        )
        template = env.get_template('view_script_template.tmpl')
        
        script_content = template.render(
            viewName=self.viewName
        )

        with open(f"./scripts/{self.viewCleanerScript}", "w") as script_file:
            script_file.write(script_content)

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
