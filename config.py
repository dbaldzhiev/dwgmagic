import os

# Single path configuration
DMM_PATH = os.getenv("DMM_PATH", "C:/dwgmagic2")

# AutoCAD Paths
accpathv = {str(year): f"C:/Program Files/Autodesk/AutoCAD {year}/accoreconsole.exe" for year in range(2017, 2026)}

# Flags and Parameters
verbose = False
xrefXplodeToggle = False
deadline = 120
sheetThreading = True
viewThreading = False

# Logging Configuration
log_encoding = "utf-16-le"
log_level = "DEBUG"
