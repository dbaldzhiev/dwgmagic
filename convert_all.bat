@echo off
setlocal enabledelayedexpansion

:: Set AutoCAD installation path (modify if needed)
set ACCORECONSOLE="C:\Program Files\Autodesk\AutoCAD 2025\accoreconsole.exe"

:: Directory containing the DWG files
set DWG_DIR=%CD%

:: AutoCAD script file
set SCRIPT=C:\dwgmagic\convert.scr

:: Process each DWG file in the folder
for %%F in (*.dwg) do (
    echo Processing %%F...
    %ACCORECONSOLE% /i "%%F" /s "%SCRIPT%"
)

echo Conversion complete.
pause
