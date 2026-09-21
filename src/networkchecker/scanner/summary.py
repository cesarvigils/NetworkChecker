"""Weekly (or any-window) stability summary built from logged scanner events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Union

from .storage import ScannerStorage


@dataclass
class StabilitySummary:
    window_days: int
    disconnection_count: int
    total_downtime_seconds: float
    uptime_percent: float
    longest_outage_seconds: float

    def to_text(self) -> str:
        lines = [
            f"Network Stability Summary — last {self.window_days} day(s)",
            "-" * 44,
            f"Disconnection events : {self.disconnection_count}",
            f"Total downtime       : {self.total_downtime_seconds / 60:.1f} minutes",
            f"Longest single outage: {self.longest_outage_seconds / 60:.1f} minutes",
            f"Estimated uptime     : {self.uptime_percent:.3f}%",
        ]
        return "\n".join(lines)


def build_summary(db_path: Union[str, Path], days: int = 7) -> StabilitySummary:
    storage = ScannerStorage(db_path)
    since = datetime.utcnow() - timedelta(days=days)
    events = storage.events_since(since)

    disconnections = [e for e in events if e[0] == "disconnected"]
    reconnections = [e for e in events if e[0] == "reconnected"]

    outage_durations: List[float] = []
    for _, _, detail in reconnections:
        if detail and "downtime_seconds=" in detail:
            try:
                outage_durations.append(float(detail.split("=", 1)[1]))
            except ValueError:
                pass

    total_downtime = sum(outage_durations)
    longest = max(outage_durations) if outage_durations else 0.0
    window_seconds = max(days, 1) * 86400
    uptime_percent = max(0.0, round(100.0 * (1 - total_downtime / window_seconds), 3))

    return StabilitySummary(
        window_days=days,
        disconnection_count=len(disconnections),
        total_downtime_seconds=total_downtime,
        uptime_percent=uptime_percent,
        longest_outage_seconds=longest,
    )
