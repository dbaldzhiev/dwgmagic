@echo off
setlocal
REM Update DWGMAGIC in place: git pull for checkouts, latest GitHub release otherwise.
REM Pass /relaunch to reopen the GUI when the update finishes.
set "APP_DIR=%~dp0"
set "RELAUNCH="
if /i "%~1"=="/relaunch" set "RELAUNCH=-Relaunch"
if not exist "%APP_DIR%update.ps1" (
    echo ERROR: update.ps1 not found next to this script.
    pause
    exit /b 1
)
REM Run the updater from TEMP so it can safely replace the application files.
copy /y "%APP_DIR%update.ps1" "%TEMP%\dwgmagic_update.ps1" >nul
REM exit /b must share the line: this script gets overwritten mid-run by the
REM update itself, and cmd would otherwise resume reading it at a stale offset.
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\dwgmagic_update.ps1" -AppDir "%APP_DIR%." %RELAUNCH% & exit /b
