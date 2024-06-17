import os

paths = {
    "dmm": os.getenv("DMM_PATH", "C:/dwgmagic2"),
}

accpathv = {str(year): f"C:/Program Files/Autodesk/AutoCAD {year}/accoreconsole.exe" for year in range(2017, 2026)}

verbose = False
xrefXplodeToggle = False
deadline = 120
sheetThreading = True
viewThreading = False

# New configuration parameters
log_encoding = "utf-16-le"
log_level = "DEBUG"
