"""Wi-Fi SSID lookup: network name, signal, and (where available) connect time.

Windows uses ``netsh wlan show interfaces`` for the SSID/signal/link speed
and a PowerShell WLAN-AutoConfig event-log query for "connected since"
(event ID 8001 is logged on every successful association). Linux uses
``nmcli``/``iwgetid``, with ``nmcli connection.timestamp`` for the connect
time. macOS uses the bundled ``airport`` utility. Every path degrades to a
clear ``error`` message instead of raising, since headless machines, wired
connections, and locked-down environments are all normal to encounter.
"""

from __future__ import annotations

import platform
import re
import subprocess
from datetime import datetime
from typing import Optional

from ..models import SSIDInfo

_SUBPROCESS_TIMEOUT = 8


def _run(cmd, timeout=_SUBPROCESS_TIMEOUT) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )


def _unsupported(message: str) -> SSIDInfo:
    return SSIDInfo(
        ssid=None,
        signal_percent=None,
        link_speed_mbps=None,
        connected_since=None,
        interface_name=None,
        supported=False,
        error=message,
    )


# --------------------------------------------------------------------------
# Windows
# --------------------------------------------------------------------------

def _windows_connected_since() -> Optional[datetime]:
    ps_command = (
        "Get-WinEvent -LogName 'Microsoft-Windows-WLAN-AutoConfig/Operational' "
        "-FilterXPath \"*[System[EventID=8001]]\" -MaxEvents 1 "
        "| Select-Object -ExpandProperty TimeCreated "
        "| Get-Date -Format o"
    )
    try:
        result = _run(["powershell", "-NoProfile", "-Command", ps_command], timeout=6)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    timestamp = result.stdout.strip()
    if result.returncode != 0 or not timestamp:
        return None
    try:
        return datetime.fromisoformat(timestamp)
    except ValueError:
        return None


def _windows_ssid() -> SSIDInfo:
    try:
        result = _run(["netsh", "wlan", "show", "interfaces"])
    except FileNotFoundError:
        return _unsupported("'netsh' is not available on this system.")
    except subprocess.TimeoutExpired:
        return _unsupported("Timed out querying the wireless interface.")

    text = result.stdout or ""
    if not text.strip():
        return _unsupported("No wireless interface found, or Wi-Fi is disabled.")

    def grab(pattern: str) -> Optional[str]:
        match = re.search(pattern, text, re.MULTILINE)
        return match.group(1).strip() if match else None

    ssid = grab(r"^\s*SSID\s*:\s*(.+)$")
    state = grab(r"^\s*State\s*:\s*(.+)$")
    signal_raw = grab(r"^\s*Signal\s*:\s*(\d+)%")
    speed_raw = grab(r"^\s*Receive rate \(Mbps\)\s*:\s*([\d.]+)")
    iface = grab(r"^\s*Name\s*:\s*(.+)$")

    signal = int(signal_raw) if signal_raw else None
    speed = float(speed_raw) if speed_raw else None

    if not ssid or (state and "connected" not in state.lower()):
        return SSIDInfo(
            ssid=None,
            signal_percent=signal,
            link_speed_mbps=speed,
            connected_since=None,
            interface_name=iface,
            supported=True,
            error="Not currently connected to a Wi-Fi network.",
        )

    return SSIDInfo(
        ssid=ssid,
        signal_percent=signal,
        link_speed_mbps=speed,
        connected_since=_windows_connected_since(),
        interface_name=iface,
        supported=True,
        error=None,
    )


# --------------------------------------------------------------------------
# Linux
# --------------------------------------------------------------------------

def _linux_connected_since(connection_name: str) -> Optional[datetime]:
    try:
        result = _run(["nmcli", "-g", "connection.timestamp", "connection", "show", connection_name])
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    if result.returncode == 0 and value.isdigit():
        return datetime.fromtimestamp(int(value))
    return None


def _linux_ssid() -> SSIDInfo:
    ssid = None
    signal = None
    iface = None

    try:
        result = _run(["nmcli", "-t", "-f", "active,ssid,signal,device", "dev", "wifi"])
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split(":")
                if len(parts) >= 4 and parts[0] == "yes":
                    ssid, signal_raw, iface = parts[1], parts[2], parts[3]
                    signal = int(signal_raw) if signal_raw.isdigit() else None
                    break
    except FileNotFoundError:
        pass

    if not ssid:
        try:
            result = _run(["iwgetid", "-r"])
            if result.returncode == 0 and result.stdout.strip():
                ssid = result.stdout.strip()
        except FileNotFoundError:
            pass

    if not ssid:
        return _unsupported(
            "No Wi-Fi connection detected (nmcli/iwgetid unavailable, or you're on Ethernet)."
        )

    return SSIDInfo(
        ssid=ssid,
        signal_percent=signal,
        link_speed_mbps=None,
        connected_since=_linux_connected_since(ssid),
        interface_name=iface,
        supported=True,
        error=None,
    )


# --------------------------------------------------------------------------
# macOS
# --------------------------------------------------------------------------

_AIRPORT_PATH = (
    "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
)


def _macos_ssid() -> SSIDInfo:
    try:
        result = _run([_AIRPORT_PATH, "-I"])
    except FileNotFoundError:
        return _unsupported("The macOS 'airport' utility was not found on this system.")

    ssid = None
    signal = None
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("SSID:"):
            ssid = line.split(":", 1)[1].strip()
        elif line.startswith("agrCtlRSSI:"):
            try:
                rssi = int(line.split(":", 1)[1].strip())
                signal = max(0, min(100, 2 * (rssi + 100)))
            except ValueError:
                pass

    if not ssid:
        return _unsupported("Not currently connected to a Wi-Fi network.")

    return SSIDInfo(
        ssid=ssid,
        signal_percent=signal,
        link_speed_mbps=None,
        connected_since=None,
        interface_name="en0",
        supported=True,
        error=None,
    )


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def get_ssid_info() -> SSIDInfo:
    """Return details about the currently connected Wi-Fi network, if any."""
    system = platform.system()
    if system == "Windows":
        return _windows_ssid()
    if system == "Linux":
        return _linux_ssid()
    if system == "Darwin":
        return _macos_ssid()
    return _unsupported(f"SSID lookup is not implemented for platform '{system}'.")
