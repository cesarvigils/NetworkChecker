"""Entry point PyInstaller bundles as NetworkChecker-GUI.exe (windowed GUI)."""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from networkchecker.gui import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
