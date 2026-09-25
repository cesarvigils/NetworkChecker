"""Plain dataclasses describing the result of each network check.

Every result carries its own optional ``error`` field instead of raising,
so a failure in one check (e.g. no internet) never prevents the rest of a
full report from running.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple


@dataclass
class SSIDInfo:
    ssid: Optional[str]
    signal_percent: Optional[int]
    link_speed_mbps: Optional[float]
    connected_since: Optional[datetime]
    interface_name: Optional[str]
    supported: bool
    error: Optional[str] = None


@dataclass
class PingResult:
    target: str
    sent: int
    received: int
    loss_percent: float
    min_ms: Optional[float]
    avg_ms: Optional[float]
    max_ms: Optional[float]
    jitter_ms: Optional[float]
    samples_ms: List[float] = field(default_factory=list)
    rating: str = "Unknown"
    method: str = "icmp"
    error: Optional[str] = None


@dataclass
class PacketLossResult:
    target: str
    packets_sent: int
    packets_received: int
    loss_percent: float
    note: str
    error: Optional[str] = None


@dataclass
class IPInfo:
    public_ip: Optional[str]
    city: Optional[str]
    region: Optional[str]
    country: Optional[str]
    isp: Optional[str]
    org: Optional[str]
    asn: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    source: Optional[str]
    error: Optional[str] = None

    @property
    def location(self) -> str:
        """"City, Region, Country", skipping any parts the provider didn't return."""
        parts = [p for p in (self.city, self.region, self.country) if p]
        return ", ".join(parts) if parts else "unknown"


@dataclass
class SpeedResult:
    download_mbps: Optional[float]
    upload_mbps: Optional[float]
    ping_ms: Optional[float]
    server_name: Optional[str]
    server_location: Optional[str]
    error: Optional[str] = None


@dataclass
class CarrierInfo:
    isp: Optional[str] = None
    organization: Optional[str] = None
    asn: Optional[str] = None
    connection_type: Optional[str] = None
    mobile_carrier: Optional[str] = None
    error: Optional[str] = None


@dataclass
class FullReport:
    generated_at: datetime
    ssid: SSIDInfo
    ping: PingResult
    packet_loss: PacketLossResult
    ip_info: IPInfo
    carrier: CarrierInfo
    speed: Optional[SpeedResult] = None


def result_to_dict(result) -> dict:
    """Convert any of the dataclasses above into a JSON-serialisable dict."""
    data = asdict(result)
    return _stringify_datetimes(data)


def _stringify_datetimes(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _stringify_datetimes(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_stringify_datetimes(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_stringify_datetimes(v) for v in value)
    return value
