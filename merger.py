# merger.py
import re
import os
import time
import subprocess as sp
import multiprocessing as mp
from threading import Thread
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

class Project:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        self.project_name = os.path.basename(os.getcwd())
        self.setup_environment()
        self.display_hierarchical_tree()
        self.sheets = self.process_sheets()
        self.generate_scripts()
        self.confirm_sheets_existence()
        self.run_project_script()

    def setup_environment(self):
        self.filenames = os.listdir(f"{os.getcwd()}/derevitized/")
        self.accpath = checks.acc_version()
        self.sheet_names_list = sorted(
            [fname for fname in self.filenames if re.match(r"(?!(?:.*-View-\d*)|(?:.*-rvt-))(^.*)(?:\.dwg$)", fname)]
        )
        self.xrefXplodeToggle = True

    def display_hierarchical_tree(self):
        tree = Tree(f" [bold orange1]{self.project_name}[/bold orange1]", guide_style="bold orange1")
        for sheet_name in self.sheet_names_list:
            sheet_branch = tree.add(f" [wheat1]{sheet_name}[/wheat1]")
            view_names_on_sheet = list(filter(re.compile(f"{sheet_name.replace('.dwg', '')}-View-\\d+").match, self.filenames))
            for view_name in view_names_on_sheet:
                view_number= re.search(f"{sheet_name.replace(".dwg",'')}-View-(.+).dwg",view_name).group(1)
                view_branch = sheet_branch.add(f" [sky_blue2]{view_name}[/sky_blue2]")
                regggex = f"{sheet_name.replace(".dwg",'')}-.+-rvt-{(view_number)}.+.dwg" 
                xrefs_in_view= list(filter(re.compile(regggex).match, self.filenames))
                for xref in xrefs_in_view:
                    view_branch.add(f" [blue]{xref}[/blue]")

        console.print(tree)

    def process_sheets(self):
        results = []
        if cfg.sheetThreading:
            try:
                with mp.Pool(mp.cpu_count()) as pool, Progress() as progress:
                    task = progress.add_task("Processing Sheets", total=len(self.sheet_names_list))
                    for sheet in pool.imap_unordered(Sheet.process_sheet, [(s, self) for s in self.sheet_names_list]):
                        results.append(sheet)
                        progress.advance(task)
            except Exception as e:
                console.print(f"Error processing sheets: {str(e)}", style="bold red")
        else:
            results = [Sheet.process_sheet((s, self)) for s in self.sheet_names_list]
        return results

    def generate_scripts(self):
        sg.generate_project_script(self.sheet_names_list, self.xrefXplodeToggle, self.sheets, log_dir=self.log_dir)
        sg.generate_manual_master_merge_script(self.xrefXplodeToggle, self.sheets, log_dir=self.log_dir)
        sg.generate_manual_master_merge_bat(self.accpath, log_dir=self.log_dir)

    def confirm_sheets_existence(self):
        timeout = time.time() + cfg.deadline
        while True:
            existence = [(s, os.path.isfile(s.clean_sheet_file_path)) for s in self.sheets]
            if all(ex[1] for ex in existence) or time.time() > timeout:
                log_and_print("All sheets derevitization confirmed!", style="bold green")
                break
            else:
                if cfg.verbose:
                    log_and_print(f"Time left: {timeout - time.time()}", None)
                    log_and_print("\n".join([f"{s.clean_sheet_file_path} is {ex}" for s, ex in existence]), None)
                time.sleep(1)

    def run_project_script(self):
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
            task = progress.add_task("Processing the Merge", total=total_commands)
            while True:
                output = process.stdout.readline()
                log_and_print(f"{(output.strip())}", mmlg, style="bold yellow")
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
    def __init__(self, sheet_name, project):
        self.acc = project.accpath
        self.sheet_name = sheet_name.replace(".dwg", "")
        self.working_file = sheet_name
        self.sheet_cleaner_script = f"{self.sheet_name.upper()}_SHEET.scr"
        self.view_names_on_sheet_list = list(filter(re.compile(f"{self.sheet_name}-View-\\d+").match, project.filenames))
        self.views_on_sheet = self.process_views(project)
        sg.generate_sheet_script(self.sheet_name, self.views_on_sheet, log_dir=project.log_dir)
        self.run_sheet_cleaner()
        self.clean_sheet_file_path = f"{os.getcwd()}/derevitized/{self.sheet_name}_xrefed.dwg"

    @staticmethod
    def process_sheet(args):
        return Sheet(*args)

    def process_views(self, project):
        views = []
        if cfg.viewThreading:
            try:
                with Progress() as progress:
                    task = progress.add_task(f"Processing Views for Sheet {self.sheet_name}", total=len(self.view_names_on_sheet_list))
                    threads = []
                    for view in self.view_names_on_sheet_list:
                        thread = Thread(target=self.process_sheet_view, args=(view, project, views, progress, task))
                        thread.start()
                        threads.append(thread)
                    for thread in threads:
                        thread.join()
            except Exception as e:
                console.print(f"Error processing views for sheet {self.sheet_name}: {str(e)}", style="bold red")
        else:
            with Progress() as progress:
                task = progress.add_task(f"Processing Views for Sheet {self.sheet_name}", total=len(self.view_names_on_sheet_list))
                for view in self.view_names_on_sheet_list:
                    views.append(View.process_view((view, project)))
                    progress.advance(task)
        return views

    def process_sheet_view(self, view, project, views, progress, task):
        views.append(View.process_view((view, project)))
        progress.advance(task)

    def run_sheet_cleaner(self):
        slg = lg.setup_logger(f"SHEET_{self.sheet_name}")
        command = [
            self.acc,
            "/i",
            f"{os.getcwd()}/derevitized/{self.sheet_name}.dwg",
            "/s",
            f"{os.getcwd()}/scripts/{self.sheet_cleaner_script}"
        ]
        log_and_print(f"Cleaning Sheet {self.sheet_name} with Script {self.sheet_cleaner_script}", slg, style="bold yellow")
        output, err = run_command(command, log=slg, verbose=cfg.verbose)
        if output is None:
            slg.error(f"Failed to clean sheet {self.sheet_name}: {str(err)}")
        else:
            try:
                os.remove(f"{os.getcwd()}/derevitized/{self.working_file}")
            except Exception as e:
                slg.error(f"Failed to remove file {self.working_file}: {str(e)}")

class View:
    def __init__(self, view_name, project):
        self.acc = project.accpath
        self.view_name = view_name.replace(".dwg", "")
        self.view_indx = re.search(r"\d+-View-(\d+).dwg", view_name).group(1)
        self.parent_sheet_indx = re.search(r"(\d+)-View-\d+.dwg", view_name).group(1)
        self.view_cleaner_script = f"{self.view_name.upper()}.scr"
        sg.generate_view_script(self.view_name, log_dir=project.log_dir)
        self.run_view_cleaner()

    @staticmethod
    def process_view(args):
        return View(*args)

    def run_view_cleaner(self):
        vlg = lg.setup_logger(f"VIEW_{self.view_name}")
        command = [
            self.acc,
            "/i",
            f"{os.getcwd()}/derevitized/{self.view_name}.dwg",
            "/s",
            f"{os.getcwd()}/scripts/{self.view_cleaner_script}"
        ]
        vlg.debug(f"Cleaning View {self.view_name} with Script {self.view_cleaner_script}")
        log_and_print(f"Cleaning View {self.view_name} with Script {self.view_cleaner_script}", vlg, style="bold yellow")
        output, err = run_command(command, log=vlg, verbose=cfg.verbose)
        if output is None:
            vlg.error(f"Failed to clean view {self.view_name}: {str(err)}")

if __name__ == "__main__":
    # Main execution logic for merger can go here if needed
    pass
