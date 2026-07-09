@echo off
setlocal
REM Open the DWGMAGIC GUI preloaded with the selected directory and start the run
if "%~1"=="" (
    echo Usage: %~nx0 ^<project directory^>
    exit /b 1
)
set "TARGET=%~1"
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" main.py "%TARGET%" --autorun
    exit /b 0
)
if exist "venv\Scripts\python.exe" (
    start "" "venv\Scripts\python.exe" main.py "%TARGET%" --autorun
    exit /b 0
)
where pythonw >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw main.py "%TARGET%" --autorun
    exit /b 0
)
where py >nul 2>&1
if %errorlevel%==0 (
    start "" py -3 main.py "%TARGET%" --autorun
    exit /b 0
)
where python >nul 2>&1
if %errorlevel%==0 (
    start "" python main.py "%TARGET%" --autorun
    exit /b 0
)
echo ERROR: No Python interpreter was found. Run install.bat first.
pause
exit /b 9009
