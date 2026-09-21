"""Application-wide constants and platform-specific paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "NetworkChecker"
VERSION = "1.0.0"

DEFAULT_PING_TARGET = "8.8.8.8"
DEFAULT_PACKET_LOSS_TARGET = "8.8.8.8"
DEFAULT_SCAN_TARGETS = [("1.1.1.1", 443), ("8.8.8.8", 443), ("9.9.9.9", 443)]
DEFAULT_SCAN_INTERVAL_SECONDS = 30


def app_data_dir() -> Path:
    """Return (and ensure) a per-user, per-OS directory for app state."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home())
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    directory = Path(base) / APP_NAME
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def scanner_db_path() -> Path:
    return app_data_dir() / "scanner.db"
