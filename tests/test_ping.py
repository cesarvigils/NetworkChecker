import socket
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from networkchecker.checks import ping


LINUX_PING_OUTPUT = """PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
64 bytes from 8.8.8.8: icmp_seq=1 ttl=115 time=12.3 ms
64 bytes from 8.8.8.8: icmp_seq=2 ttl=115 time=14.1 ms
64 bytes from 8.8.8.8: icmp_seq=3 ttl=115 time=13.0 ms

--- 8.8.8.8 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2003ms
"""

WINDOWS_PING_OUTPUT = """
Pinging 8.8.8.8 with 32 bytes of data:
Reply from 8.8.8.8: bytes=32 time=15ms TTL=115
Reply from 8.8.8.8: bytes=32 time<1ms TTL=115
Reply from 8.8.8.8: bytes=32 time=18ms TTL=115

Ping statistics for 8.8.8.8:
    Packets: Sent = 3, Received = 3, Lost = 0 (0% loss),
"""


def _completed(stdout, returncode=0):
    return subprocess.CompletedProcess(args=["ping"], returncode=returncode, stdout=stdout, stderr="")


def test_icmp_ping_parses_linux_output():
    with patch("networkchecker.checks.ping.platform.system", return_value="Linux"), \
         patch("networkchecker.checks.ping._run", return_value=_completed(LINUX_PING_OUTPUT)):
        result = ping.ping_host(target="8.8.8.8", count=3, timeout_s=1)

    assert result.method == "icmp"
    assert result.sent == 3
    assert result.received == 3
    assert result.loss_percent == 0.0
    assert result.avg_ms == round((12.3 + 14.1 + 13.0) / 3, 2)
    assert result.rating in {"Good", "Excellent", "Fair", "Poor"}
    assert result.error is None


def test_icmp_ping_parses_windows_output():
    with patch("networkchecker.checks.ping.platform.system", return_value="Windows"), \
         patch("networkchecker.checks.ping._run", return_value=_completed(WINDOWS_PING_OUTPUT)):
        result = ping.ping_host(target="8.8.8.8", count=3, timeout_s=1)

    assert result.method == "icmp"
    assert result.received == 3
    # "time<1ms" should be parsed as 1ms by the regex fallback.
    assert 1.0 in result.samples_ms


def test_ping_falls_back_to_tcp_when_ping_binary_missing():
    with patch("networkchecker.checks.ping._icmp_ping", side_effect=FileNotFoundError()), \
         patch("networkchecker.checks.ping._tcp_fallback_ping", return_value=[10.0, 12.0, 11.0]) as tcp_mock:
        result = ping.ping_host(target="example.com", count=3, timeout_s=1)

    tcp_mock.assert_called_once()
    assert result.method == "tcp"
    assert result.received == 3
    assert result.error is None


def test_ping_reports_error_when_no_responses():
    with patch("networkchecker.checks.ping._icmp_ping", return_value=[]):
        result = ping.ping_host(target="unreachable.example", count=4, timeout_s=1)

    assert result.received == 0
    assert result.loss_percent == 100.0
    assert result.avg_ms is None
    assert result.error is not None


def test_tcp_fallback_ping_times_successful_connects():
    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    with patch("networkchecker.checks.ping.socket.create_connection", return_value=FakeConn()):
        samples = ping._tcp_fallback_ping("1.2.3.4", count=5, timeout_s=1)

    assert len(samples) == 5
    assert all(s >= 0 for s in samples)


def test_rating_thresholds():
    assert ping._rate(5) == "Excellent"
    assert ping._rate(35) == "Good"
    assert ping._rate(80) == "Fair"
    assert ping._rate(500) == "Poor"
    assert ping._rate(None) == "Unknown"
