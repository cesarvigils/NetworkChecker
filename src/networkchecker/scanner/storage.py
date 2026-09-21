"""SQLite-backed event log for the background scanner."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Union

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp);
"""


class ScannerStorage:
    """Thin wrapper around a small SQLite database of connectivity events."""

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def log_event(self, event_type: str, detail: str = "") -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO events (event_type, timestamp, detail) VALUES (?, ?, ?)",
                (event_type, datetime.utcnow().isoformat(), detail),
            )
            conn.commit()

    def events_since(self, since: datetime) -> List[Tuple[str, str, str]]:
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                "SELECT event_type, timestamp, detail FROM events "
                "WHERE timestamp >= ? ORDER BY timestamp",
                (since.isoformat(),),
            )
            return cursor.fetchall()

    def all_events(self) -> List[Tuple[str, str, str]]:
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                "SELECT event_type, timestamp, detail FROM events ORDER BY timestamp"
            )
            return cursor.fetchall()

    def clear(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute("DELETE FROM events")
            conn.commit()
