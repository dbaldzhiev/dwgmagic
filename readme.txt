DWGMAGIC v3.00
Overview
DWGMAGIC is a tool designed to automate the process of combining sheets exported from Autodesk Revit into a single DWG file. This script is particularly useful in workflows where delivering all project sheets in modelspace is required, even though this approach is considered outdated. DWGMAGIC arranges the exported sheets in modelspace, XREFs all the DWGs, binds them, and cleans up the resulting file.

How It Works
The script operates in several steps:

Export Sheets from Revit: Export sheets with the "Export views on sheets and links as external references" option enabled and use the "Automatic-Short" naming convention. The sheets should be sequentially numbered (1, 2, 3, etc.) and saved to an empty directory.
Run DWGMAGIC: Execute the script with the command python main.py TARGETDIR, where TARGETDIR is the path to the directory containing the exported sheets.
Script Execution: DWGMAGIC generates several .SCR files, which are executed using accoreconsole.exe, the command-line version of AutoCAD.
Processing: The script processes the DWG files, organizes them, and outputs:

/derevitized: Modified DWG files.
/originals: Unchanged original exported DWG files.
/scripts: Generated and executed .SCR files.
acclog.log: Log file.
MasterXref.dwg: DWG file with all sheets XREFed into it.
MasterMerged.dwg: DWG file with all sheets bound and exploded.

Requirements
Python installed on your system.
AutoCAD installed with versions from 2017 to 2026.
Dependencies listed in requirements.txt:
Jinja2==3.1.4
rich==13.7.1

Installation
Install Python: Ensure Python is installed on your system.
Install Dependencies: Run the install_py-req.bat batch file to install the required Python packages.
Run the Registry File: Execute the DWGMAGIC.reg file to add DWGMAGIC to the context menu.
Configure AutoCAD: Add the dwgmagic2 folder to trusted folders in AutoCAD.
Start Merging: Run the script with your target directory as described above.
Configuration
Configuration settings are specified in config.py:

DMM_PATH: Default path for the DWGMAGIC tool.
accpathv: Dictionary specifying paths to accoreconsole.exe for AutoCAD versions from 2017 to 2026.
verbose: Flag for enabling verbose output.
xref_xplode_toggle: Toggle for XREF explode option.
log_encoding: Encoding for log files.
log_level: Log level setting.

Adding DWGMAGIC to the Context Menu
To add DWGMAGIC as a context menu item, follow these steps:
Run DWGMAGIC.reg: Execute the DWGMAGIC.reg file. This will modify your Windows registry to include DWGMAGIC in the context menu for folders.
Context Menu Usage: Right-click on any folder and select DWGMAGIC from the context menu to execute the script for that directory.

Usage
Run the script with the following command:

python main.py <path_to_directory>
You can optionally specify a log directory:

python main.py <path_to_directory> --log-dir my_logs
Example:

python main.py C:/Projects/ExportedSheets
This command will process all the DWG files in the C:/Projects/ExportedSheets directory according to the DWGMAGIC workflow.

Launching the GUI
-----------------
You can start a simple graphical interface with:

python main.py --gui

From the GUI you can select the project directory and run the tool without manually typing commands. The interface also lets you choose a log directory and displays the contents of the log once the run finishes.

Contributions
This script was originally developed by Dimitar Baldzhiev. Contributions and suggestions for improvement are welcome. If you encounter any bugs or have ideas for enhancements, please contribute to the project.

This readme covers the essential aspects of DWGMAGIC v3.00, including its functionality, requirements, installation steps, configuration, and usage instructions. Enjoy using DWGMAGIC for efficient DWG file management!