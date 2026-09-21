from datetime import datetime, timedelta

from networkchecker.scanner.monitor import NetworkMonitor
from networkchecker.scanner.storage import ScannerStorage
from networkchecker.scanner.summary import build_summary


def test_storage_logs_and_reads_events(tmp_path):
    storage = ScannerStorage(tmp_path / "scanner.db")
    storage.log_event("disconnected")
    storage.log_event("reconnected", "downtime_seconds=42")

    events = storage.all_events()
    assert len(events) == 2
    assert events[0][0] == "disconnected"
    assert events[1][2] == "downtime_seconds=42"


def test_storage_events_since_filters_by_time(tmp_path):
    storage = ScannerStorage(tmp_path / "scanner.db")
    storage.log_event("disconnected")

    future_cutoff = datetime.utcnow() + timedelta(hours=1)
    assert storage.events_since(future_cutoff) == []

    past_cutoff = datetime.utcnow() - timedelta(hours=1)
    assert len(storage.events_since(past_cutoff)) == 1


def test_build_summary_computes_downtime_and_uptime(tmp_path):
    db_path = tmp_path / "scanner.db"
    storage = ScannerStorage(db_path)
    storage.log_event("disconnected")
    storage.log_event("reconnected", "downtime_seconds=600")  # 10 minutes
    storage.log_event("disconnected")
    storage.log_event("reconnected", "downtime_seconds=300")  # 5 minutes

    summary = build_summary(db_path, days=7)

    assert summary.disconnection_count == 2
    assert summary.total_downtime_seconds == 900
    assert summary.longest_outage_seconds == 600
    assert 0 < summary.uptime_percent < 100
    assert "Network Stability Summary" in summary.to_text()


def test_build_summary_with_no_events_is_100_percent_uptime(tmp_path):
    summary = build_summary(tmp_path / "empty.db", days=7)
    assert summary.disconnection_count == 0
    assert summary.uptime_percent == 100.0


def test_monitor_logs_disconnect_and_reconnect_transitions(tmp_path):
    import time
    import unittest.mock as mock

    db_path = tmp_path / "scanner.db"
    monitor = NetworkMonitor(db_path, interval_s=0.02)

    # up, down, down, up, then padded with "up" so the thread never runs out
    # of scripted values before the test calls stop().
    connectivity_sequence = [True, False, False, True] + [True] * 50

    with mock.patch.object(
        NetworkMonitor, "_check_connectivity", side_effect=connectivity_sequence
    ):
        monitor.start()
        time.sleep(0.02 * 8)
        monitor.stop()

    events = monitor.storage.all_events()
    event_types = [e[0] for e in events]
    assert event_types == ["disconnected", "reconnected"]
    assert "downtime_seconds=" in events[1][2]


def test_monitor_start_stop_lifecycle(tmp_path):
    monitor = NetworkMonitor(tmp_path / "scanner.db", interval_s=0.05)
    assert not monitor.is_running
    monitor.start()
    assert monitor.is_running
    monitor.stop()
    assert not monitor.is_running
