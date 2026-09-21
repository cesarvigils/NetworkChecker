# Full Network Checker Interface

A cross-platform network diagnostics tool with both a desktop GUI and a
command-line interface. It checks your Wi-Fi/SSID, latency, packet loss,
public IP and geolocation, ISP/carrier info, and download/upload speed —
plus an optional background scanner that tracks disconnections over time
and produces a weekly stability summary.

It ships as installable Python (`pip install .`), and can be packaged into
a standalone Windows **`.exe`** or **`.msi`** installer — see
[documents/PACKAGING.md](documents/PACKAGING.md).

## Features

| Feature | Status | Notes |
|---|---|---|
| SSID Check (name, signal, connected-at) | ✅ | Windows/Linux/macOS; "connected since" is Windows/Linux only |
| Ping / latency test with a rating | ✅ | Excellent / Good / Fair / Poor, based on average round-trip time |
| Packet loss test | ✅ | Combined round-trip loss (see caveat below) |
| IP check + approximate geolocation | ✅ | City-level accuracy, via public IP-geolocation APIs |
| Download speed test | ✅ | Via speedtest.net infrastructure |
| Upload speed test | ✅ | Via speedtest.net infrastructure |
| Carrier / ISP information | ✅ | ISP/ASN from IP lookup; mobile carrier name on Windows with a cellular adapter |
| Optional stability scanner | ✅ | Background downtime/disconnection logging + weekly summary |

**Packet loss caveat:** ICMP echo (ping) only measures *combined*
round-trip loss — it cannot tell you whether packets were lost on the way
out or the way back without a cooperating server at both ends (e.g.
`iperf3`). True directional packet loss is tracked as a future
improvement in [documents/futureactions.md](documents/futureactions.md).

## Installation

Requires Python 3.9+.

```bash
git clone <this-repo>
cd NetworkChecker
pip install .
```

For development (editable install + test/build tooling):

```bash
pip install -e ".[dev]"
```

## Usage

### Command line

```bash
networkchecker --help

networkchecker ssid                 # Wi-Fi network name, signal, connected-since
networkchecker ping --target 1.1.1.1 --count 20
networkchecker packet-loss
networkchecker ip                   # public IP + approximate location
networkchecker carrier              # ISP / mobile carrier info
networkchecker speed                # download + upload speed test
networkchecker full                 # run everything and print a full report
networkchecker full --no-speed --json   # machine-readable, skip the slow speed test

# Optional background stability scanner
networkchecker scanner watch --interval 30   # runs until Ctrl+C, logs to a local DB
networkchecker scanner summary --days 7      # weekly stability report
networkchecker scanner events --limit 20     # recent raw connectivity events
```

Every subcommand supports `--json` for scripting, and exits non-zero if the
check itself reports an error (e.g. you're offline).

### Desktop GUI

```bash
python -m networkchecker
# or, after an editable install:
networkchecker-gui
```

Buttons run each check individually or all at once ("Run Full Check"), and
a panel at the bottom starts/stops the background scanner and shows the
weekly summary. The GUI needs Tkinter, which ships with the standard
Windows/macOS Python installers (on Debian/Ubuntu Linux, install it
separately with `sudo apt install python3-tk`).

### Packaged as .exe / .msi

Once built (see [documents/PACKAGING.md](documents/PACKAGING.md)), end
users just run the installer — no Python required on their machine.

## Project layout

```
src/networkchecker/
    checks/       SSID, ping, packet loss, IP/geolocation, speed, carrier
    scanner/      Background monitor, SQLite storage, weekly summary
    utils/        Small cross-platform helpers
    app.py        Orchestrates a "full report" across all checks
    cli.py        argparse-based command-line interface
    gui.py        Tkinter desktop GUI
packaging/        PyInstaller specs, Inno Setup script, WiX (.msi) script
tests/             pytest suite (subprocess/network calls are mocked)
documents/        Packaging guide and future roadmap
```

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

Tests mock all subprocess and network calls, so they run offline and don't
depend on your actual Wi-Fi/ISP.

## Usage Policy

You can use this **free**, but keep in mind: the author is not responsible
for anything you do with it. You are the sole owner of your actions. In
other words, be careful with it. Network, location, and ISP data comes from
third-party services and your own OS tools, and its accuracy is not
guaranteed.

## License

MIT — see the disclaimer above.
