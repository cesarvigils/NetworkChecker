@echo off
setlocal
REM Builds a true Windows Installer .msi with the WiX Toolset (v3.11+).
REM Requires dist\NetworkChecker-GUI.exe and dist\networkchecker.exe to
REM already exist (run scripts\build_exe.bat first) and candle.exe /
REM light.exe to be on PATH.
REM
REM Usage:  scripts\build_msi.bat

cd /d "%~dp0.."

if not exist "dist\NetworkChecker-GUI.exe" (
    echo dist\NetworkChecker-GUI.exe not found. Run scripts\build_exe.bat first.
    exit /b 1
)

where candle >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo WiX Toolset ("candle"/"light"^) not found on PATH.
    echo Install it from https://wixtoolset.org/releases/ and re-run this script.
    exit /b 1
)

if not exist "build\wix" mkdir "build\wix"

echo === Compiling WiX source ===
candle -dSourceDir=dist packaging\wix\NetworkChecker.wxs -o build\wix\ || goto :error

echo === Linking MSI ===
light build\wix\NetworkChecker.wixobj -ext WixUIExtension -o dist\NetworkChecker.msi || goto :error

echo === Done: dist\NetworkChecker.msi ===
exit /b 0

:error
echo MSI build failed.
exit /b 1
