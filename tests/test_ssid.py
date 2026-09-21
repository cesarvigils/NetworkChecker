import subprocess
from unittest.mock import patch

from networkchecker.checks import ssid


WINDOWS_INTERFACES_OUTPUT = """
Name                   : Wi-Fi
Description            : Intel(R) Wireless-AC 9560
State                  : connected
SSID                   : HomeNetwork_5G
Signal                 : 82%
Receive rate (Mbps)    : 866
"""

WINDOWS_DISCONNECTED_OUTPUT = """
Name                   : Wi-Fi
State                  : disconnected
"""


def _completed(stdout, returncode=0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def test_windows_ssid_parses_connected_network():
    with patch("networkchecker.checks.ssid.platform.system", return_value="Windows"), \
         patch("networkchecker.checks.ssid._run", return_value=_completed(WINDOWS_INTERFACES_OUTPUT)), \
         patch("networkchecker.checks.ssid._windows_connected_since", return_value=None):
        info = ssid.get_ssid_info()

    assert info.ssid == "HomeNetwork_5G"
    assert info.signal_percent == 82
    assert info.link_speed_mbps == 866.0
    assert info.interface_name == "Wi-Fi"
    assert info.supported is True
    assert info.error is None


def test_windows_ssid_reports_not_connected():
    with patch("networkchecker.checks.ssid.platform.system", return_value="Windows"), \
         patch("networkchecker.checks.ssid._run", return_value=_completed(WINDOWS_DISCONNECTED_OUTPUT)):
        info = ssid.get_ssid_info()

    assert info.ssid is None
    assert info.error == "Not currently connected to a Wi-Fi network."


def test_windows_ssid_handles_missing_netsh():
    with patch("networkchecker.checks.ssid.platform.system", return_value="Windows"), \
         patch("networkchecker.checks.ssid._run", side_effect=FileNotFoundError()):
        info = ssid.get_ssid_info()

    assert info.supported is False
    assert "netsh" in info.error


def test_linux_ssid_uses_nmcli_active_line():
    nmcli_output = "yes:HomeNetwork_5G:82:wlan0\nno:OtherNetwork:40:wlan0\n"
    with patch("networkchecker.checks.ssid.platform.system", return_value="Linux"), \
         patch("networkchecker.checks.ssid._run") as run_mock:
        run_mock.side_effect = [
            _completed(nmcli_output),  # nmcli dev wifi
            _completed("1700000000"),  # nmcli connection.timestamp
        ]
        info = ssid.get_ssid_info()

    assert info.ssid == "HomeNetwork_5G"
    assert info.signal_percent == 82
    assert info.interface_name == "wlan0"
    assert info.connected_since is not None


def test_linux_ssid_falls_back_to_iwgetid():
    with patch("networkchecker.checks.ssid.platform.system", return_value="Linux"), \
         patch("networkchecker.checks.ssid._run") as run_mock:
        run_mock.side_effect = [
            FileNotFoundError(),          # nmcli missing
            _completed("HomeNetwork_5G"),  # iwgetid -r
            _completed(""),               # nmcli connection.timestamp (unavailable)
        ]
        info = ssid.get_ssid_info()

    assert info.ssid == "HomeNetwork_5G"


def test_linux_ssid_no_wifi_detected():
    with patch("networkchecker.checks.ssid.platform.system", return_value="Linux"), \
         patch("networkchecker.checks.ssid._run", side_effect=FileNotFoundError()):
        info = ssid.get_ssid_info()

    assert info.supported is False
    assert info.ssid is None


def test_unsupported_platform():
    with patch("networkchecker.checks.ssid.platform.system", return_value="Plan9"):
        info = ssid.get_ssid_info()

    assert info.supported is False
    assert "Plan9" in info.error
