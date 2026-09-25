# Packaging NetworkChecker into a Windows .exe / .msi

This project is pure Python, so building a native Windows package has to
happen **on Windows** (PyInstaller compiles for the host platform only — it
can't cross-compile a Windows binary from Linux/macOS). The pipeline below
is exactly what [`.github/workflows/build-windows.yml`](../.github/workflows/build-windows.yml)
runs automatically on `windows-latest` GitHub Actions runners; you can run
the same steps locally on a Windows machine.

## Pipeline overview

```
Python source  --PyInstaller-->  NetworkChecker-GUI.exe + networkchecker.exe
                                         |
                          +--------------+--------------+
                          |                             |
                    Inno Setup                     WiX Toolset
                          |                             |
              NetworkChecker-Setup.exe          NetworkChecker.msi
              (installer, easiest to build)     (true MSI package)
```

You only need one of Inno Setup or WiX, not both — pick whichever output
format you want to ship. Inno Setup is simpler to set up; WiX produces a
"real" `.msi` if that's a hard requirement (e.g. for enterprise deployment
via Group Policy / SCCM).

## 1. Prerequisites (Windows)

- Python 3.9+ (from python.org; check "Add python.exe to PATH")
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) — for the `.exe` installer, **and/or**
- [WiX Toolset v3.11+](https://wixtoolset.org/releases/) — for the `.msi`

## 2. Build the executables

From the repository root, in a Windows terminal:

```bat
scripts\build_exe.bat
```

This installs dependencies, runs PyInstaller against both spec files in
`packaging/pyinstaller/`, and (if `iscc` is on PATH) also compiles the Inno
Setup installer. Equivalent manual steps:

```bat
pip install -r requirements.txt -r requirements-dev.txt
pyinstaller packaging\pyinstaller\NetworkChecker.spec
pyinstaller packaging\pyinstaller\NetworkCheckerCLI.spec
```

Output: `dist\NetworkChecker-GUI.exe` (windowed GUI) and
`dist\networkchecker.exe` (console app, for scripting and the
`scanner watch` long-running mode).

> The console exe is deliberately named plain `networkchecker` so that
> typing `networkchecker <command>` in a terminal runs it. Windows matches
> exe names case-insensitively, so the GUI must **not** be called
> `NetworkChecker.exe` — it would shadow the CLI and silently open a
> window instead of printing results.

> Both spec files exclude `cryptography`/`OpenSSL` — `requests` only needs
> the standard library's `ssl` module, and excluding them avoids a known
> PyInstaller/`cryptography` (Rust extension) conflict on some build hosts.

### Adding a custom icon

Drop an `app_icon.ico` file into `packaging/pyinstaller/` — both spec files
already look for it and will embed it automatically if present.

## 3a. Build the `.exe` installer (Inno Setup)

```bat
iscc packaging\inno\NetworkChecker.iss
```

Output: `packaging\inno\Output\NetworkChecker-Setup.exe`. This installs
both executables, creates Start Menu (and optionally Desktop) shortcuts,
adds the install folder to the user's `PATH` (so `networkchecker` works
from any new terminal; untick the option to skip it), and generates an
uninstaller.

## 3b. Build the `.msi` (WiX Toolset)

```bat
scripts\build_msi.bat
```

Equivalent manual steps:

```bat
candle -dSourceDir=dist packaging\wix\NetworkChecker.wxs -o build\wix\
light build\wix\NetworkChecker.wixobj -ext WixUIExtension -o dist\NetworkChecker.msi
```

Output: `dist\NetworkChecker.msi`. Double-clicking it (or `msiexec /i
NetworkChecker.msi`) installs both executables, Start Menu + Desktop
shortcuts, and registers a proper uninstall entry in "Apps & Features".

## 4. Continuous Integration

`.github/workflows/build-windows.yml` runs the test suite on every push/PR,
then — on a `windows-latest` runner — builds both executables, the Inno
Setup installer, and the MSI, uploading them as workflow artifacts (these
expire after 90 days).

## 5. Publishing a release

Pushing a version tag publishes a **GitHub Release** with the installers
attached:

```bash
git checkout main && git pull
git tag v1.0.0            # must match [project].version in pyproject.toml
git push origin v1.0.0
```

The workflow then builds everything and creates a release named
`NetworkChecker v1.0.0`, with auto-generated release notes and these
downloads: `NetworkChecker-Setup.exe`, `NetworkChecker.msi`, and the two
standalone executables. If the tag doesn't match the version in
`pyproject.toml`, the build fails before anything is published, so bump
the version first (see below).

## Versioning

The version string lives in three places that should be bumped together:

- `src/networkchecker/config.py` (`VERSION`)
- `pyproject.toml` (`[project].version`)
- `packaging/pyinstaller/version_info.txt`, `packaging/inno/NetworkChecker.iss`, `packaging/wix/NetworkChecker.wxs`

## Troubleshooting

- **"iscc is not recognized"** — Inno Setup wasn't added to PATH; use the
  full path to `ISCC.exe` (usually under `C:\Program Files (x86)\Inno Setup 6\`).
- **`candle`/`light` not found** — same idea for WiX; its `bin` folder
  (e.g. `C:\Program Files (x86)\WiX Toolset v3.11\bin`) needs to be on PATH.
- **Antivirus flags the unsigned .exe** — expected for any unsigned
  PyInstaller binary. Code-signing is listed as a future improvement in
  [futureactions.md](futureactions.md).
- **GUI window doesn't appear / crashes on launch** — make sure you built
  from `NetworkChecker.spec` (which sets `console=False`); run
  `dist\networkchecker.exe --help` first to confirm the underlying
  Python code itself is working.
