# Future Actions & Roadmap

Ideas for where NetworkChecker could go next, roughly ordered by how soon
they'd be worth tackling. None of this is committed — it's a backlog to
pull from, not a promise.

## Near-term (accuracy & polish)

- **True directional packet loss.** Right now `packet-loss` reports
  combined round-trip loss via ICMP, because a single-ended ping can't
  separate upstream from downstream. Bundling (or optionally shelling out
  to) `iperf3` against a public or self-hosted server would let us report
  upload-loss and download-loss independently.
- **Config file support.** A `~/.config/NetworkChecker/config.toml` (or
  `%APPDATA%\NetworkChecker\config.toml`) for default ping targets, scan
  interval, latency rating thresholds, and preferred speed-test server —
  so power users don't have to pass the same flags every time.
- **Code-signing the installer.** Unsigned `.exe`/`.msi` files trigger
  Windows SmartScreen and antivirus warnings. An Authenticode certificate
  (or a free option like SignPath for OSS projects) would fix that.
- **Historical data export.** `scanner events --json` already dumps raw
  events; add a `scanner export --format csv` for spreadsheet-friendly
  output, plus a retention/pruning policy so the SQLite DB doesn't grow
  forever on a machine left running for months.
- **Configurable ping rating thresholds.** The Excellent/Good/Fair/Poor
  buckets in `checks/ping.py` are currently fixed constants; expose them
  as CLI flags / config values for gamers, VoIP users, etc. who have
  different tolerance for latency.

## Mid-term (features)

- **System tray integration.** Minimize the GUI to a tray icon that shows
  current connectivity status at a glance, with a right-click menu for
  "Run Full Check" / "Weekly Summary" / "Quit". Would use `pystray` or
  platform-native APIs.
- **Auto-start scanner on login.** A Windows Task Scheduler entry (or
  Startup folder shortcut) created by the installer, and an equivalent
  systemd user unit / LaunchAgent for Linux/macOS, so the stability
  scanner runs continuously without the user remembering to start it.
- **Downtime alerts.** Optional email or webhook (Slack/Discord) 
  notification when the scanner detects a disconnection longer than a
  configurable threshold.
- **Charts in the GUI.** A simple latency-over-time and
  uptime-over-time chart (e.g. via `matplotlib`'s Tk backend) instead of
  the current plain-text weekly summary.
- **DNS resolution timing.** A dedicated check that times DNS lookups
  separately from ping, to help distinguish "slow DNS" from "slow
  network" as a root cause.
- **Traceroute visualization.** Useful for diagnosing *where* latency or
  loss is being introduced, not just that it's happening.
- **True second-package split.** The README originally framed the
  scanner as an optional "second package." Today it's an opt-in module
  within the same install; a follow-up could split it into a genuinely
  separate PyPI package / installer component for people who only want
  the on-demand checks.

## Long-term / exploratory

- **Auto-update mechanism.** Check GitHub Releases for a newer version
  and prompt to download, so users aren't stuck on stale installers.
- **Cross-platform native packaging.** A macOS `.pkg`/`.dmg` and Linux
  `.deb`/`.rpm`/Flatpak/AppImage, using the same PyInstaller-built
  binaries as a base, so the "one install, all checks" experience isn't
  Windows-only.
- **Plugin architecture.** Let third parties register additional checks
  (e.g. VPN detection, DNS-over-HTTPS status) without modifying core code.
- **Multi-device dashboard.** Optional opt-in cloud sync so a household
  or small office can see stability history across several machines in
  one place — would need a real backend and privacy-conscious design.
- **Localization.** Extract user-facing strings (CLI/GUI) for translation.
- **Accessibility pass on the GUI.** Screen-reader labels, full keyboard
  navigation, high-contrast theme.
- **Broader automated test coverage.** Headless GUI tests (e.g. via
  `pytest` + `Xvfb` on Linux CI) and integration tests that spin up a
  local TCP/HTTP server instead of mocking, to catch regressions the
  current unit-level mocks might miss.
- **IPv6-aware checks.** Ping, packet loss, and IP lookup currently favor
  IPv4 targets; add explicit IPv6 variants and let users choose or
  auto-detect which stack to test.
