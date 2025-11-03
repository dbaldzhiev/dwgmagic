@echo off
setlocal
REM Launch the DWGMAGIC GUI from the installation directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
if exist "venv\Scripts\pythonw.exe" (
    "venv\Scripts\pythonw.exe" main.py --gui %*
    exit /b %errorlevel%
)
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" main.py --gui %*
    exit /b %errorlevel%
)
if exist "Scripts\pythonw.exe" (
    "Scripts\pythonw.exe" main.py --gui %*
    exit /b %errorlevel%
)
if exist "Scripts\python.exe" (
    "Scripts\python.exe" main.py --gui %*
    exit /b %errorlevel%
)
where py >nul 2>&1
if %errorlevel%==0 (
    py -3 main.py --gui %*
    exit /b %errorlevel%
)
where pythonw >nul 2>&1
if %errorlevel%==0 (
    pythonw main.py --gui %*
    exit /b %errorlevel%
)
where python >nul 2>&1
if %errorlevel%==0 (
    python main.py --gui %*
    exit /b %errorlevel%
)
echo ERROR: No Python interpreter was found on PATH.
exit /b 9009
