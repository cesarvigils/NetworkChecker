@echo off
setlocal enabledelayedexpansion
REM Builds NetworkChecker-GUI.exe (GUI) and networkchecker.exe (console)
REM with PyInstaller, then compiles the Inno Setup installer if "iscc" is
REM on PATH. Run this from Windows with Python 3.9+ installed.
REM
REM Usage:  scripts\build_exe.bat

cd /d "%~dp0.."

echo === Installing build dependencies ===
python -m pip install --upgrade pip || goto :error
python -m pip install -r requirements.txt -r requirements-dev.txt || goto :error

echo === Building NetworkChecker-GUI.exe (GUI) ===
python -m PyInstaller --noconfirm --clean packaging\pyinstaller\NetworkChecker.spec || goto :error

echo === Building networkchecker.exe (console) ===
python -m PyInstaller --noconfirm --clean packaging\pyinstaller\NetworkCheckerCLI.spec || goto :error

echo === PyInstaller output is in dist\ ===
dir dist

where iscc >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo === Compiling Inno Setup installer ===
    iscc packaging\inno\NetworkChecker.iss || goto :error
    echo === Installer written to packaging\inno\Output\NetworkChecker-Setup.exe ===
) else (
    echo Inno Setup ("iscc") not found on PATH — skipping installer build.
    echo Install it from https://jrsoftware.org/isinfo.php to produce a Setup.exe.
)

echo === Done ===
exit /b 0

:error
echo Build failed.
exit /b 1
