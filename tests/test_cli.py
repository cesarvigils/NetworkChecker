import json
from unittest.mock import patch

from networkchecker import cli
from networkchecker.models import IPInfo, PingResult


def _fake_ping(target="8.8.8.8", count=10, timeout_s=2.0):
    return PingResult(
        target=target, sent=count, received=count, loss_percent=0.0,
        min_ms=10.0, avg_ms=12.0, max_ms=15.0, jitter_ms=1.0,
        samples_ms=[12.0] * count, rating="Good", method="icmp", error=None,
    )


def _fake_ip_info_ok():
    return IPInfo(
        public_ip="203.0.113.5", city="Springfield", region="IL", country="USA",
        isp="Example ISP", org="Example Org", asn="AS64500", latitude=1.0, longitude=2.0,
        source="ip-api.com", error=None,
    )


def test_ping_command_prints_human_readable(capsys):
    with patch("networkchecker.cli.ping_host", side_effect=_fake_ping):
        rc = cli.main(["ping", "--count", "3"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "Target" in out
    assert "Rating" in out


def test_ping_command_json_output_is_valid(capsys):
    with patch("networkchecker.cli.ping_host", side_effect=_fake_ping):
        rc = cli.main(["ping", "--json"])

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["target"] == "8.8.8.8"
    assert rc == 0


def test_ip_command_returns_nonzero_on_error(capsys):
    error_info = IPInfo(
        public_ip=None, city=None, region=None, country=None, isp=None, org=None,
        asn=None, latitude=None, longitude=None, source=None, error="offline",
    )
    with patch("networkchecker.cli.get_ip_info", return_value=error_info):
        rc = cli.main(["ip"])

    assert rc == 1
    assert "offline" in capsys.readouterr().out


def test_ip_command_returns_zero_on_success(capsys):
    with patch("networkchecker.cli.get_ip_info", return_value=_fake_ip_info_ok()):
        rc = cli.main(["ip"])

    assert rc == 0
    assert "203.0.113.5" in capsys.readouterr().out


def test_scanner_summary_command(tmp_path, capsys):
    db_path = str(tmp_path / "scanner.db")
    rc = cli.main(["scanner", "summary", "--db-path", db_path, "--days", "3"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Network Stability Summary" in out


def test_scanner_events_command_empty(tmp_path, capsys):
    db_path = str(tmp_path / "scanner.db")
    rc = cli.main(["scanner", "events", "--db-path", db_path])
    out = capsys.readouterr().out
    assert rc == 0
    assert "No scanner events" in out


def test_version_flag(capsys):
    try:
        cli.main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    out = capsys.readouterr().out
    assert "networkchecker" in out


def test_no_arguments_prints_help_instead_of_erroring(capsys):
    with patch("networkchecker.cli._launched_by_double_click", return_value=False):
        rc = cli.main([])

    assert rc == 0
    assert "usage: networkchecker" in capsys.readouterr().out


def test_no_arguments_waits_for_enter_when_double_clicked(capsys):
    with patch("networkchecker.cli._launched_by_double_click", return_value=True), \
            patch("builtins.input", return_value="") as fake_input:
        rc = cli.main([])

    assert rc == 0
    fake_input.assert_called_once()
    assert "open a terminal" in capsys.readouterr().out


def test_ip_command_shows_location_and_coordinates(capsys):
    with patch("networkchecker.cli.get_ip_info", return_value=_fake_ip_info_ok()):
        cli.main(["ip"])

    out = capsys.readouterr().out
    assert "Springfield, IL, USA" in out
    assert "Coordinates    : 1.0, 2.0" in out
