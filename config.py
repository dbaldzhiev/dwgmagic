# config.py
import os

# Single path configuration
DMM_PATH = os.getenv("DMM_PATH", "C:/dwgmagic")

# AutoCAD Paths
accpathv = {str(year): f"C:/Program Files/Autodesk/AutoCAD {year}/accoreconsole.exe" for year in range(2017, 2026)}

# Flags and Parameters
verbose = False
xref_xplode_toggle = True

# Logging Configuration
#log_encoding = "utf-16-le"
log_encoding = "utf-8"
log_level = "DEBUG"
