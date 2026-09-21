"""Background thread that periodically probes connectivity.

Connectivity is checked with plain TCP connects to a handful of well-known,
highly-available hosts (Cloudflare, Google, Quad9 DNS on port 443) rather
than ICMP, so it needs no elevated privileges and works identically on
every platform. A state transition (up -> down or down -> up) is logged
as an event; reconnection events record how long the outage lasted.
"""

from __future__ import annotations

import socket
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Union

from ..config import DEFAULT_SCAN_INTERVAL_SECONDS, DEFAULT_SCAN_TARGETS
from .storage import ScannerStorage


class NetworkMonitor:
    """Polls connectivity on a background thread and logs state changes."""

    def __init__(
        self,
        db_path: Union[str, Path],
        interval_s: float = DEFAULT_SCAN_INTERVAL_SECONDS,
        targets: Optional[List[Tuple[str, int]]] = None,
        connect_timeout_s: float = 3.0,
    ):
        self.storage = ScannerStorage(db_path)
        self.interval_s = interval_s
        self.targets = targets or list(DEFAULT_SCAN_TARGETS)
        self.connect_timeout_s = connect_timeout_s
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._was_up = True
        self._down_since: Optional[datetime] = None

    def _check_connectivity(self) -> bool:
        for host, port in self.targets:
            try:
                with socket.create_connection((host, port), timeout=self.connect_timeout_s):
                    return True
            except OSError:
                continue
        return False

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            up = self._check_connectivity()
            now = datetime.utcnow()

            if up and not self._was_up:
                downtime = (now - self._down_since).total_seconds() if self._down_since else 0.0
                self.storage.log_event("reconnected", f"downtime_seconds={downtime:.0f}")
                self._down_since = None
            elif not up and self._was_up:
                self._down_since = now
                self.storage.log_event("disconnected")

            self._was_up = up
            self._stop_event.wait(self.interval_s)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="NetworkMonitor")
        self._thread.start()

    def stop(self, wait: bool = True) -> None:
        self._stop_event.set()
        if wait and self._thread:
            self._thread.join(timeout=self.interval_s + 5)

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())
