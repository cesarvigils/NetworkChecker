#!/usr/bin/env bash
# Run NetworkChecker straight from source (no build step), for development.
# Usage: scripts/run_dev.sh [cli args...]
#   scripts/run_dev.sh full --no-speed
#   scripts/run_dev.sh            # launches the GUI if a display + tkinter are available
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -e ".[dev]"

if [ "$#" -eq 0 ]; then
    python3 -m networkchecker
else
    python3 -m networkchecker.cli "$@"
fi
