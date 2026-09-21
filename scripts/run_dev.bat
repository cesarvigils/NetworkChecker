@echo off
REM Run NetworkChecker straight from source (no build step), for development.
REM Usage: scripts\run_dev.bat [cli args...]
REM   scripts\run_dev.bat full --no-speed
REM   scripts\run_dev.bat            (launches the GUI)
setlocal
cd /d "%~dp0.."

if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -q -e ".[dev]"

if "%~1"=="" (
    python -m networkchecker
) else (
    python -m networkchecker.cli %*
)
