"""Latency testing with a "normal range" rating, per the README's request.

Prefers the OS's own ``ping`` binary (no elevated privileges needed on any
of the three major platforms) and parses per-packet round-trip times out
of its text output. If ``ping`` isn't on PATH — sandboxed containers,
minimal server images — falls back to timing raw TCP connects to the
target on port 443, which needs no external binary at all.
"""

from __future__ import annotations

import platform
import re
import socket
import statistics
import subprocess
import time
from typing import List, Tuple

from ..config import DEFAULT_PING_TARGET
from ..models import PingResult

DEFAULT_COUNT = 10

# (upper bound in ms, rating label). The last bucket catches everything above.
_RATING_THRESHOLDS_MS: Tuple[Tuple[float, str], ...] = (
    (20.0, "Excellent"),
    (50.0, "Good"),
    (100.0, "Fair"),
)


def _rate(avg_ms) -> str:
    if avg_ms is None:
        return "Unknown"
    for threshold, label in _RATING_THRESHOLDS_MS:
        if avg_ms <= threshold:
            return label
    return "Poor"


def _run(cmd, timeout) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )


def _icmp_ping(target: str, count: int, timeout_s: float) -> List[float]:
    """Run the system ping binary and return parsed RTT samples in ms.

    Raises FileNotFoundError/subprocess.TimeoutExpired/OSError on failure
    so the caller can fall back to the TCP method.
    """
    if platform.system() == "Windows":
        cmd = ["ping", "-n", str(count), "-w", str(int(timeout_s * 1000)), target]
        pattern = re.compile(r"time[=<]([\d.]+)\s*ms", re.IGNORECASE)
    else:
        cmd = ["ping", "-c", str(count), "-W", str(max(1, int(round(timeout_s)))), target]
        pattern = re.compile(r"time=([\d.]+)\s*ms")

    result = _run(cmd, timeout=timeout_s * count + 10)
    return [float(m) for m in pattern.findall(result.stdout)]


def _tcp_fallback_ping(target: str, count: int, timeout_s: float, port: int = 443) -> List[float]:
    """No-privilege latency proxy: time TCP handshakes instead of ICMP echoes."""
    samples: List[float] = []
    for _ in range(count):
        start = time.perf_counter()
        try:
            with socket.create_connection((target, port), timeout=timeout_s):
                samples.append((time.perf_counter() - start) * 1000)
        except OSError:
            pass
    return samples


def ping_host(
    target: str = DEFAULT_PING_TARGET,
    count: int = DEFAULT_COUNT,
    timeout_s: float = 2.0,
) -> PingResult:
    """Ping ``target`` ``count`` times and summarize latency/loss/jitter."""
    method = "icmp"
    try:
        samples = _icmp_ping(target, count, timeout_s)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        samples = _tcp_fallback_ping(target, count, timeout_s)
        method = "tcp"

    sent = count
    received = len(samples)
    loss_percent = round(100.0 * (sent - received) / sent, 1) if sent else 100.0

    if samples:
        min_ms = round(min(samples), 2)
        max_ms = round(max(samples), 2)
        avg_ms = round(statistics.mean(samples), 2)
        jitter_ms = round(statistics.pstdev(samples), 2) if len(samples) > 1 else 0.0
    else:
        min_ms = max_ms = avg_ms = jitter_ms = None

    error = None
    if not received:
        error = (
            f"No responses from {target}. It may be unreachable, blocking ICMP, "
            "or you may be offline."
        )

    return PingResult(
        target=target,
        sent=sent,
        received=received,
        loss_percent=loss_percent,
        min_ms=min_ms,
        avg_ms=avg_ms,
        max_ms=max_ms,
        jitter_ms=jitter_ms,
        samples_ms=[round(s, 2) for s in samples],
        rating=_rate(avg_ms),
        method=method,
        error=error,
    )
