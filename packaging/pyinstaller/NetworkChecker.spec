# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: NetworkChecker.exe (windowed GUI, onefile).

Build with:
    pyinstaller packaging/pyinstaller/NetworkChecker.spec

Output lands in dist/NetworkChecker.exe. See documents/PACKAGING.md for the
full build -> Inno Setup / WiX -> installer pipeline.
"""

import sys
from pathlib import Path

SPEC_DIR = Path(SPECPATH)
PROJECT_ROOT = SPEC_DIR.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
ICON_PATH = SPEC_DIR / "app_icon.ico"
VERSION_FILE = SPEC_DIR / "version_info.txt"

sys.path.insert(0, str(SRC_DIR))

block_cipher = None

a = Analysis(
    [str(SPEC_DIR / "launcher_gui.py")],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=[],
    hiddenimports=["speedtest"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # requests/urllib3 can *optionally* use pyOpenSSL; we don't need it (the
    # stdlib ssl module is enough), and excluding it avoids dragging in the
    # cryptography package's compiled Rust extension on some build hosts.
    excludes=["cryptography", "OpenSSL"],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="NetworkChecker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(VERSION_FILE) if VERSION_FILE.exists() else None,
    icon=str(ICON_PATH) if ICON_PATH.exists() else None,
)
