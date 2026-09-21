"""Best-effort detection of how the machine is currently connected."""

from __future__ import annotations

import socket

from ..checks.ssid import get_ssid_info


def detect_connection_type() -> str:
    """Return "Wi-Fi", "Ethernet", or "Unknown" as a best-effort guess."""
    ssid_info = get_ssid_info()
    if ssid_info.ssid:
        return "Wi-Fi"

    try:
        # Any outbound-routable socket implies *some* active interface;
        # if it isn't Wi-Fi (checked above), assume wired.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.settimeout(1)
            probe.connect(("8.8.8.8", 80))
        return "Ethernet"
    except OSError:
        return "Unknown"
