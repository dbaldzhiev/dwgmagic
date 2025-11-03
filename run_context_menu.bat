@echo off
setlocal
REM Execute the DWGMAGIC pipeline against a selected directory
if "%~1"=="" (
    echo Usage: %~nx0 ^<project directory^>
    exit /b 1
)
set "TARGET=%~1"
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" main.py "%TARGET%"
    exit /b %errorlevel%
)
if exist "Scripts\python.exe" (
    "Scripts\python.exe" main.py "%TARGET%"
    exit /b %errorlevel%
)
if exist "venv\Scripts\pythonw.exe" (
    "venv\Scripts\pythonw.exe" main.py "%TARGET%"
    exit /b %errorlevel%
)
where py >nul 2>&1
if %errorlevel%==0 (
    py -3 main.py "%TARGET%"
    exit /b %errorlevel%
)
where python >nul 2>&1
if %errorlevel%==0 (
    python main.py "%TARGET%"
    exit /b %errorlevel%
)
echo ERROR: No Python interpreter was found on PATH.
exit /b 9009
