@echo off
setlocal
REM Launch the DWGMAGIC GUI (default front-end) from the installation directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" main.py %*
    exit /b 0
)
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" main.py %*
    exit /b %errorlevel%
)
where pythonw >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw main.py %*
    exit /b 0
)
where py >nul 2>&1
if %errorlevel%==0 (
    py -3 main.py %*
    exit /b %errorlevel%
)
where python >nul 2>&1
if %errorlevel%==0 (
    python main.py %*
    exit /b %errorlevel%
)
echo ERROR: No Python interpreter was found. Run install.bat first.
pause
exit /b 9009
