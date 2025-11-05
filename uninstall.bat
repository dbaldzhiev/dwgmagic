@echo off
setlocal
REM Remove DWGMAGIC integration from the current user profile
if "%LOCALAPPDATA%"=="" (
    echo ERROR: LOCALAPPDATA environment variable is not defined.
    exit /b 1
)
set "APP_NAME=DWGMAGIC"
set "INSTALL_DIR=%LOCALAPPDATA%\dwgmagic"
set "CONTEXT_KEY=Software\Classes\Directory\shell\DWGMAGIC"
set "DESKTOP_LINK=%USERPROFILE%\Desktop\%APP_NAME% GUI.lnk"
set "PUBLIC_DESKTOP=%PUBLIC%\Desktop\%APP_NAME% GUI.lnk"

echo Removing context menu entry...
reg delete "HKCU\%CONTEXT_KEY%" /f >nul 2>nul

echo Removing desktop shortcuts...
if exist "%DESKTOP_LINK%" del /f /q "%DESKTOP_LINK%"
if exist "%PUBLIC_DESKTOP%" del /f /q "%PUBLIC_DESKTOP%"

echo Removing application files from "%INSTALL_DIR%"...
if exist "%INSTALL_DIR%" (
    rmdir /s /q "%INSTALL_DIR%"
)

echo Uninstallation complete.
exit /b 0
