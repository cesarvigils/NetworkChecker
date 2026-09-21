from unittest.mock import patch

from networkchecker.checks import packet_loss
from networkchecker.models import PingResult


def test_packet_loss_test_delegates_to_ping_and_adds_note():
    fake_ping_result = PingResult(
        target="8.8.8.8",
        sent=30,
        received=27,
        loss_percent=10.0,
        min_ms=10.0,
        avg_ms=15.0,
        max_ms=25.0,
        jitter_ms=3.0,
        samples_ms=[10.0] * 27,
        rating="Good",
        method="icmp",
        error=None,
    )
    with patch("networkchecker.checks.packet_loss.ping_host", return_value=fake_ping_result) as ping_mock:
        result = packet_loss.packet_loss_test(target="8.8.8.8", count=30)

    ping_mock.assert_called_once_with(target="8.8.8.8", count=30, timeout_s=1.5)
    assert result.packets_sent == 30
    assert result.packets_received == 27
    assert result.loss_percent == 10.0
    assert "combined round-trip" in result.note
    assert result.error is None


def test_packet_loss_test_propagates_error():
    fake_ping_result = PingResult(
        target="10.0.0.1", sent=10, received=0, loss_percent=100.0,
        min_ms=None, avg_ms=None, max_ms=None, jitter_ms=None,
        samples_ms=[], rating="Unknown", method="tcp", error="No responses from 10.0.0.1.",
    )
    with patch("networkchecker.checks.packet_loss.ping_host", return_value=fake_ping_result):
        result = packet_loss.packet_loss_test(target="10.0.0.1")

    assert result.error == "No responses from 10.0.0.1."
