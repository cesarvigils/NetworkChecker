"""Tkinter desktop GUI.

Tkinter ships with the standard CPython installer on Windows/macOS, so this
adds no extra dependency for the packaged .exe/.msi build. Every network
call runs on a background thread — Tkinter itself is not thread-safe, so
worker threads only ever push results onto a ``queue.Queue`` and the main
thread drains it on a periodic ``after()`` timer.
"""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext, ttk
from typing import Callable

from . import config
from .app import run_full_report
from .checks.carrier import get_carrier_info
from .checks.ip_info import get_ip_info
from .checks.packet_loss import packet_loss_test
from .checks.ping import ping_host
from .checks.ssid import get_ssid_info
from .checks.speed import run_speed_test
from .models import FullReport
from .scanner.monitor import NetworkMonitor
from .scanner.summary import build_summary
from .utils.platform_utils import detect_connection_type

_POLL_INTERVAL_MS = 150


class NetworkCheckerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{config.APP_NAME} v{config.VERSION}")
        self.geometry("760x560")
        self.minsize(620, 440)

        self._queue: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self._monitor: NetworkMonitor | None = None

        self._build_widgets()
        self.after(_POLL_INTERVAL_MS, self._drain_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- layout -----------------------------------------------------------

    def _build_widgets(self) -> None:
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        buttons = [
            ("SSID Check", self.run_ssid_check),
            ("Ping Test", self.run_ping_check),
            ("Packet Loss", self.run_packet_loss_check),
            ("IP / Location", self.run_ip_check),
            ("Carrier Info", self.run_carrier_check),
            ("Speed Test", self.run_speed_check),
            ("Run Full Check", self.run_full_check),
        ]
        for label, command in buttons:
            ttk.Button(toolbar, text=label, command=command).pack(side=tk.LEFT, padx=3)

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(8, 2)).pack(
            side=tk.TOP, fill=tk.X
        )

        self.output = scrolledtext.ScrolledText(self, wrap=tk.WORD, font=("Consolas", 10))
        self.output.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.output.configure(state=tk.DISABLED)

        scanner_frame = ttk.LabelFrame(self, text="Background Stability Scanner (optional)", padding=8)
        scanner_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 8))

        self.scanner_state_var = tk.StringVar(value="Stopped")
        ttk.Label(scanner_frame, text="Status:").pack(side=tk.LEFT)
        ttk.Label(scanner_frame, textvariable=self.scanner_state_var, width=10).pack(side=tk.LEFT)
        ttk.Button(scanner_frame, text="Start", command=self.start_scanner).pack(side=tk.LEFT, padx=4)
        ttk.Button(scanner_frame, text="Stop", command=self.stop_scanner).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            scanner_frame, text="Weekly Summary", command=self.show_weekly_summary
        ).pack(side=tk.LEFT, padx=4)

    # -- output helpers -----------------------------------------------------

    def _write(self, text: str) -> None:
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def _clear(self) -> None:
        self.output.configure(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        self.output.configure(state=tk.DISABLED)

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _drain_queue(self) -> None:
        try:
            while True:
                job = self._queue.get_nowait()
                job()
        except queue.Empty:
            pass
        self.after(_POLL_INTERVAL_MS, self._drain_queue)

    def _run_async(self, label: str, work: Callable[[], None]) -> None:
        self._set_status(f"Running: {label}...")

        def target() -> None:
            try:
                work()
            finally:
                self._queue.put(lambda: self._set_status("Ready."))

        threading.Thread(target=target, daemon=True).start()

    # -- individual checks --------------------------------------------------

    def run_ssid_check(self) -> None:
        def work() -> None:
            info = get_ssid_info()

            def report() -> None:
                self._write("=== SSID Check ===")
                if info.error:
                    self._write(f"  {info.error}")
                else:
                    self._write(f"  SSID           : {info.ssid}")
                    self._write(f"  Signal         : {info.signal_percent}%")
                    self._write(f"  Connected since: {info.connected_since}")
                self._write("")

            self._queue.put(report)

        self._run_async("SSID check", work)

    def run_ping_check(self) -> None:
        def work() -> None:
            result = ping_host()

            def report() -> None:
                self._write("=== Ping Test ===")
                self._write(f"  Target: {result.target} (method: {result.method})")
                self._write(f"  Sent/Received: {result.sent}/{result.received} ({result.loss_percent}% loss)")
                if result.avg_ms is not None:
                    self._write(f"  Min/Avg/Max: {result.min_ms}/{result.avg_ms}/{result.max_ms} ms")
                    self._write(f"  Jitter: {result.jitter_ms} ms  |  Rating: {result.rating}")
                if result.error:
                    self._write(f"  Note: {result.error}")
                self._write("")

            self._queue.put(report)

        self._run_async("Ping test", work)

    def run_packet_loss_check(self) -> None:
        def work() -> None:
            result = packet_loss_test()

            def report() -> None:
                self._write("=== Packet Loss Test ===")
                self._write(f"  Target: {result.target}")
                self._write(f"  Loss: {result.loss_percent}% ({result.packets_received}/{result.packets_sent} received)")
                self._write(f"  Note: {result.note}")
                self._write("")

            self._queue.put(report)

        self._run_async("Packet loss test", work)

    def run_ip_check(self) -> None:
        def work() -> None:
            info = get_ip_info()

            def report() -> None:
                self._write("=== IP / Geolocation ===")
                if info.error:
                    self._write(f"  {info.error}")
                else:
                    self._write(f"  Public IP: {info.public_ip}")
                    self._write(f"  Location : {info.location}")
                    self._write(f"  ISP/Org  : {info.isp} / {info.org}")
                self._write("")

            self._queue.put(report)

        self._run_async("IP check", work)

    def run_carrier_check(self) -> None:
        def work() -> None:
            info = get_carrier_info(connection_type=detect_connection_type())

            def report() -> None:
                self._write("=== Carrier / ISP Info ===")
                if info.error:
                    self._write(f"  {info.error}")
                else:
                    self._write(f"  Connection type: {info.connection_type}")
                    self._write(f"  ISP            : {info.isp}")
                    if info.mobile_carrier:
                        self._write(f"  Mobile carrier : {info.mobile_carrier}")
                self._write("")

            self._queue.put(report)

        self._run_async("Carrier check", work)

    def run_speed_check(self) -> None:
        def progress(message: str) -> None:
            self._queue.put(lambda: self._set_status(message))

        def work() -> None:
            result = run_speed_test(progress_callback=progress)

            def report() -> None:
                self._write("=== Speed Test ===")
                if result.error:
                    self._write(f"  {result.error}")
                else:
                    self._write(f"  Download: {result.download_mbps} Mbps")
                    self._write(f"  Upload  : {result.upload_mbps} Mbps")
                    self._write(f"  Ping    : {result.ping_ms} ms")
                    self._write(f"  Server  : {result.server_name} ({result.server_location})")
                self._write("")

            self._queue.put(report)

        self._run_async("Speed test", work)

    def run_full_check(self) -> None:
        def progress(message: str) -> None:
            self._queue.put(lambda: self._set_status(message))

        def work() -> None:
            report: FullReport = run_full_report(include_speed_test=True, progress_callback=progress)
            self._queue.put(lambda: self._render_full_report(report))

        self._run_async("Full check", work)

    def _render_full_report(self, report: FullReport) -> None:
        self._write(f"===== Full Network Report — {report.generated_at.isoformat()} UTC =====")

        self._write("\n[Wi-Fi / SSID]")
        if report.ssid.error:
            self._write(f"  {report.ssid.error}")
        else:
            self._write(f"  SSID           : {report.ssid.ssid}")
            self._write(f"  Signal         : {report.ssid.signal_percent}%")
            self._write(f"  Connected since: {report.ssid.connected_since}")

        self._write("\n[Ping]")
        p = report.ping
        self._write(f"  Target: {p.target} (method: {p.method})")
        self._write(f"  Sent/Received: {p.sent}/{p.received} ({p.loss_percent}% loss)")
        if p.avg_ms is not None:
            self._write(f"  Min/Avg/Max: {p.min_ms}/{p.avg_ms}/{p.max_ms} ms  |  Jitter: {p.jitter_ms} ms  |  Rating: {p.rating}")

        self._write("\n[Packet Loss]")
        pl = report.packet_loss
        self._write(f"  Loss: {pl.loss_percent}% ({pl.packets_received}/{pl.packets_sent} received)")

        self._write("\n[IP / Geolocation]")
        if report.ip_info.error:
            self._write(f"  {report.ip_info.error}")
        else:
            ip = report.ip_info
            self._write(f"  Public IP: {ip.public_ip}")
            self._write(f"  Location : {ip.location}")
            self._write(f"  ISP/Org  : {ip.isp} / {ip.org}")

        self._write("\n[Carrier / ISP]")
        if report.carrier.error:
            self._write(f"  {report.carrier.error}")
        else:
            c = report.carrier
            self._write(f"  Connection type: {c.connection_type}")
            self._write(f"  ISP            : {c.isp}")
            if c.mobile_carrier:
                self._write(f"  Mobile carrier : {c.mobile_carrier}")

        if report.speed:
            self._write("\n[Speed Test]")
            s = report.speed
            if s.error:
                self._write(f"  {s.error}")
            else:
                self._write(f"  Download: {s.download_mbps} Mbps  |  Upload: {s.upload_mbps} Mbps  |  Ping: {s.ping_ms} ms")
        self._write("")

    # -- scanner -------------------------------------------------------------

    def start_scanner(self) -> None:
        if self._monitor and self._monitor.is_running:
            return
        self._monitor = NetworkMonitor(config.scanner_db_path())
        self._monitor.start()
        self.scanner_state_var.set("Running")
        self._write("Background scanner started.\n")

    def stop_scanner(self) -> None:
        if self._monitor:
            self._monitor.stop(wait=False)
        self.scanner_state_var.set("Stopped")
        self._write("Background scanner stopped.\n")

    def show_weekly_summary(self) -> None:
        summary = build_summary(config.scanner_db_path(), days=7)
        self._write(summary.to_text())
        self._write("")

    def _on_close(self) -> None:
        if self._monitor:
            self._monitor.stop(wait=False)
        self.destroy()


def main() -> int:
    try:
        app = NetworkCheckerApp()
    except tk.TclError as exc:
        print(
            f"Unable to start the GUI (no display available?): {exc}\n"
            "Try the command-line interface instead: networkchecker --help",
            file=sys.stderr,
        )
        return 1
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
