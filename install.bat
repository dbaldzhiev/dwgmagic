@echo off
setlocal
REM Install DWGMAGIC into the local application data folder and create integrations
if "%LOCALAPPDATA%"=="" (
    echo ERROR: LOCALAPPDATA environment variable is not defined.
    exit /b 1
)
set "APP_NAME=DWGMAGIC"
set "INSTALL_DIR=%LOCALAPPDATA%\dwgmagic"
set "SOURCE_DIR=%~dp0"
set "SHORTCUT_NAME=%APP_NAME% GUI.lnk"
set "CONTEXT_KEY=Software\Classes\Directory\shell\DWGMAGIC"

echo Installing %APP_NAME% to "%INSTALL_DIR%"...
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%" || (
        echo ERROR: Failed to create installation directory.
        exit /b 1
    )
)

echo Copying application files...
robocopy "%SOURCE_DIR%" "%INSTALL_DIR%" /MIR /R:2 /W:5 /XD ".git" ".mypy_cache" ".pytest_cache" "__pycache__" >nul
set "ROBOCOPY_EXIT=%ERRORLEVEL%"
if %ROBOCOPY_EXIT% GEQ 8 (
    echo ERROR: File copy failed with code %ROBOCOPY_EXIT%.
    exit /b %ROBOCOPY_EXIT%
)

echo Creating context menu entry...
reg add "HKCU\%CONTEXT_KEY%" /ve /d "Run with DWGMAGIC" /f >nul
reg add "HKCU\%CONTEXT_KEY%" /v "Icon" /d "\"%INSTALL_DIR%\\magic.ico\"" /f >nul
reg add "HKCU\%CONTEXT_KEY%\\command" /ve /d "\"%INSTALL_DIR%\\run_context_menu.bat\" \"%%1\"" /f >nul

if exist "%INSTALL_DIR%\magic.ico" (
    set "SHORTCUT_ICON=%INSTALL_DIR%\magic.ico"
) else (
    set "SHORTCUT_ICON=%SystemRoot%\System32\shell32.dll,0"
)
set "SHORTCUT_TARGET=%INSTALL_DIR%\run_gui.bat"
set "SHORTCUT_WORKDIR=%INSTALL_DIR%"

if exist "%SHORTCUT_TARGET%" (
    echo Creating desktop shortcut...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$shell = New-Object -ComObject WScript.Shell; $desktop = $shell.SpecialFolders.Item('Desktop'); $lnk = Join-Path $desktop '%APP_NAME% GUI.lnk'; $shortcut = $shell.CreateShortcut($lnk); $shortcut.TargetPath = $env:SHORTCUT_TARGET; $shortcut.WorkingDirectory = $env:SHORTCUT_WORKDIR; $shortcut.IconLocation = $env:SHORTCUT_ICON; $shortcut.Save()" >nul
    if errorlevel 1 (
        echo WARNING: Failed to create desktop shortcut automatically.
    ) else (
        echo Desktop shortcut created.
    )
) else (
    echo WARNING: GUI launcher script was not found; shortcut skipped.
)

echo Installation complete.
exit /b 0
