"""Command-line interface: ``networkchecker <command> [options]``.

Every command prints a human-readable report by default, or a single JSON
object with ``--json`` for scripting. Exit code is 0 on success, 1 if the
check itself reported an error (e.g. offline), 2 on a usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime

from . import config
from .app import run_full_report
from .checks.carrier import get_carrier_info
from .checks.ip_info import get_ip_info
from .checks.packet_loss import packet_loss_test
from .checks.ping import ping_host
from .checks.ssid import get_ssid_info
from .checks.speed import run_speed_test
from .models import FullReport, result_to_dict
from .scanner.monitor import NetworkMonitor
from .scanner.storage import ScannerStorage
from .scanner.summary import build_summary
from .utils.platform_utils import detect_connection_type


def _print_json(obj) -> None:
    if isinstance(obj, FullReport):
        payload = {
            "generated_at": obj.generated_at.isoformat(),
            "ssid": result_to_dict(obj.ssid),
            "ping": result_to_dict(obj.ping),
            "packet_loss": result_to_dict(obj.packet_loss),
            "ip_info": result_to_dict(obj.ip_info),
            "carrier": result_to_dict(obj.carrier),
            "speed": result_to_dict(obj.speed) if obj.speed else None,
        }
    else:
        payload = result_to_dict(obj)
    print(json.dumps(payload, indent=2))


def _had_error(*results) -> bool:
    return any(getattr(r, "error", None) for r in results if r is not None)


def _print_ssid(info) -> None:
    if info.error:
        print(f"SSID check: {info.error}")
        return
    print(f"SSID           : {info.ssid}")
    print(f"Interface      : {info.interface_name or 'unknown'}")
    print(f"Signal         : {info.signal_percent}%" if info.signal_percent is not None else "Signal         : unknown")
    if info.link_speed_mbps is not None:
        print(f"Link speed     : {info.link_speed_mbps} Mbps")
    if info.connected_since is not None:
        print(f"Connected since: {info.connected_since.isoformat()}")


def _print_ping(result) -> None:
    print(f"Target         : {result.target}  (method: {result.method})")
    print(f"Sent / Received: {result.sent} / {result.received}  ({result.loss_percent}% loss)")
    if result.avg_ms is not None:
        print(f"Min / Avg / Max: {result.min_ms} / {result.avg_ms} / {result.max_ms} ms")
        print(f"Jitter         : {result.jitter_ms} ms")
        print(f"Rating         : {result.rating}")
    if result.error:
        print(f"Note           : {result.error}")


def _print_packet_loss(result) -> None:
    print(f"Target         : {result.target}")
    print(f"Sent / Received: {result.packets_sent} / {result.packets_received}")
    print(f"Packet loss    : {result.loss_percent}%")
    print(f"Note           : {result.note}")
    if result.error:
        print(f"Error          : {result.error}")


def _print_ip(info) -> None:
    if info.error:
        print(f"IP check: {info.error}")
        return
    print(f"Public IP      : {info.public_ip}")
    print(f"Location       : {info.city}, {info.region}, {info.country}")
    print(f"ISP / Org      : {info.isp} / {info.org}")
    print(f"ASN            : {info.asn}")
    print(f"Source         : {info.source}")


def _print_speed(result) -> None:
    if result.error:
        print(f"Speed test: {result.error}")
        return
    print(f"Download       : {result.download_mbps} Mbps")
    print(f"Upload         : {result.upload_mbps} Mbps")
    print(f"Ping           : {result.ping_ms} ms")
    print(f"Server         : {result.server_name} ({result.server_location})")


def _print_carrier(info) -> None:
    if info.error:
        print(f"Carrier check: {info.error}")
        return
    print(f"Connection type: {info.connection_type}")
    print(f"ISP            : {info.isp}")
    print(f"Organization   : {info.organization}")
    print(f"ASN            : {info.asn}")
    if info.mobile_carrier:
        print(f"Mobile carrier : {info.mobile_carrier}")


def _cmd_ssid(args) -> int:
    info = get_ssid_info()
    if args.json:
        _print_json(info)
    else:
        _print_ssid(info)
    return 1 if info.error else 0


def _cmd_ping(args) -> int:
    result = ping_host(target=args.target, count=args.count, timeout_s=args.timeout)
    if args.json:
        _print_json(result)
    else:
        _print_ping(result)
    return 1 if result.error else 0


def _cmd_packet_loss(args) -> int:
    result = packet_loss_test(target=args.target, count=args.count)
    if args.json:
        _print_json(result)
    else:
        _print_packet_loss(result)
    return 1 if result.error else 0


def _cmd_ip(args) -> int:
    info = get_ip_info()
    if args.json:
        _print_json(info)
    else:
        _print_ip(info)
    return 1 if info.error else 0


def _cmd_speed(args) -> int:
    def progress(message: str) -> None:
        if not args.json:
            print(message, file=sys.stderr)

    result = run_speed_test(progress_callback=progress)
    if args.json:
        _print_json(result)
    else:
        _print_speed(result)
    return 1 if result.error else 0


def _cmd_carrier(args) -> int:
    info = get_carrier_info(connection_type=detect_connection_type())
    if args.json:
        _print_json(info)
    else:
        _print_carrier(info)
    return 1 if info.error else 0


def _cmd_full(args) -> int:
    def progress(message: str) -> None:
        if not args.json:
            print(f"... {message}", file=sys.stderr)

    report = run_full_report(include_speed_test=not args.no_speed, progress_callback=progress)

    if args.json:
        _print_json(report)
    else:
        print(f"Full Network Report — {report.generated_at.isoformat()} UTC")
        print("=" * 50)
        print("\n[Wi-Fi / SSID]")
        _print_ssid(report.ssid)
        print("\n[Ping]")
        _print_ping(report.ping)
        print("\n[Packet Loss]")
        _print_packet_loss(report.packet_loss)
        print("\n[IP / Geolocation]")
        _print_ip(report.ip_info)
        print("\n[Carrier / ISP]")
        _print_carrier(report.carrier)
        if report.speed:
            print("\n[Speed Test]")
            _print_speed(report.speed)

    errored = [report.ssid, report.ping, report.packet_loss, report.ip_info, report.carrier]
    if report.speed:
        errored.append(report.speed)
    return 1 if _had_error(*errored) else 0


def _cmd_scanner_watch(args) -> int:
    db_path = args.db_path or config.scanner_db_path()
    monitor = NetworkMonitor(db_path, interval_s=args.interval)
    print(f"Watching connectivity every {args.interval}s. Logging to {db_path}. Press Ctrl+C to stop.")
    monitor.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping scanner...")
        monitor.stop()
    return 0


def _cmd_scanner_summary(args) -> int:
    db_path = args.db_path or config.scanner_db_path()
    summary = build_summary(db_path, days=args.days)
    if args.json:
        print(json.dumps(summary.__dict__, indent=2))
    else:
        print(summary.to_text())
    return 0


def _cmd_scanner_events(args) -> int:
    db_path = args.db_path or config.scanner_db_path()
    storage = ScannerStorage(db_path)
    events = storage.all_events()[-args.limit:]
    if args.json:
        print(json.dumps(
            [{"event_type": e, "timestamp": t, "detail": d} for e, t, d in events],
            indent=2,
        ))
        return 0
    if not events:
        print("No scanner events logged yet. Run 'networkchecker scanner watch' first.")
        return 0
    for event_type, timestamp, detail in events:
        suffix = f"  ({detail})" if detail else ""
        print(f"{timestamp}  {event_type}{suffix}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="networkchecker",
        description="Full Network Checker Interface — diagnose your connection.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {config.VERSION}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_json_flag(sub):
        sub.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")

    p_ssid = subparsers.add_parser("ssid", help="Show the currently connected Wi-Fi network.")
    add_json_flag(p_ssid)
    p_ssid.set_defaults(func=_cmd_ssid)

    p_ping = subparsers.add_parser("ping", help="Ping a host and rate the latency.")
    p_ping.add_argument("--target", default=config.DEFAULT_PING_TARGET, help="Host or IP to ping.")
    p_ping.add_argument("--count", type=int, default=10, help="Number of pings to send.")
    p_ping.add_argument("--timeout", type=float, default=2.0, help="Per-packet timeout in seconds.")
    add_json_flag(p_ping)
    p_ping.set_defaults(func=_cmd_ping)

    p_loss = subparsers.add_parser("packet-loss", help="Run a dedicated packet loss test.")
    p_loss.add_argument("--target", default=config.DEFAULT_PACKET_LOSS_TARGET, help="Host or IP to test.")
    p_loss.add_argument("--count", type=int, default=30, help="Number of packets to send.")
    add_json_flag(p_loss)
    p_loss.set_defaults(func=_cmd_packet_loss)

    p_ip = subparsers.add_parser("ip", help="Show your public IP and approximate location.")
    add_json_flag(p_ip)
    p_ip.set_defaults(func=_cmd_ip)

    p_speed = subparsers.add_parser("speed", help="Run a download/upload speed test.")
    add_json_flag(p_speed)
    p_speed.set_defaults(func=_cmd_speed)

    p_carrier = subparsers.add_parser("carrier", help="Show ISP / mobile carrier information.")
    add_json_flag(p_carrier)
    p_carrier.set_defaults(func=_cmd_carrier)

    p_full = subparsers.add_parser("full", help="Run every check and print a full report.")
    p_full.add_argument("--no-speed", action="store_true", help="Skip the (slow) speed test.")
    add_json_flag(p_full)
    p_full.set_defaults(func=_cmd_full)

    p_scanner = subparsers.add_parser("scanner", help="Optional background stability scanner.")
    scanner_sub = p_scanner.add_subparsers(dest="scanner_command", required=True)

    p_watch = scanner_sub.add_parser("watch", help="Run the scanner in the foreground until Ctrl+C.")
    p_watch.add_argument("--interval", type=float, default=config.DEFAULT_SCAN_INTERVAL_SECONDS)
    p_watch.add_argument("--db-path", default=None, help="Override the scanner database path.")
    p_watch.set_defaults(func=_cmd_scanner_watch)

    p_summary = scanner_sub.add_parser("summary", help="Print a stability summary for a recent window.")
    p_summary.add_argument("--days", type=int, default=7)
    p_summary.add_argument("--db-path", default=None)
    add_json_flag(p_summary)
    p_summary.set_defaults(func=_cmd_scanner_summary)

    p_events = scanner_sub.add_parser("events", help="List recently logged connectivity events.")
    p_events.add_argument("--limit", type=int, default=50)
    p_events.add_argument("--db-path", default=None)
    add_json_flag(p_events)
    p_events.set_defaults(func=_cmd_scanner_events)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
