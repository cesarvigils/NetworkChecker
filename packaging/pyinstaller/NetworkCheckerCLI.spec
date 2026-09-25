# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: networkchecker.exe (console app, onefile).

Build with:
    pyinstaller packaging/pyinstaller/NetworkCheckerCLI.spec

Output lands in dist/networkchecker.exe. Bundled alongside the GUI exe
so scripting/automation users (and the "scanner watch" long-running mode)
have a console entry point too. It is deliberately named plain
"networkchecker" so that typing ``networkchecker <command>`` in a terminal
runs this console exe (Windows matches exe names case-insensitively, so
the GUI must not be called NetworkChecker.exe, or it would win instead).
"""

import sys
from pathlib import Path

SPEC_DIR = Path(SPECPATH)
PROJECT_ROOT = SPEC_DIR.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
VERSION_FILE = SPEC_DIR / "version_info.txt"

sys.path.insert(0, str(SRC_DIR))

block_cipher = None

a = Analysis(
    [str(SPEC_DIR / "launcher_cli.py")],
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
    name="networkchecker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(VERSION_FILE) if VERSION_FILE.exists() else None,
)
