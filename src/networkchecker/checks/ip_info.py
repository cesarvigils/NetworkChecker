"""Public IP address and approximate geolocation.

Tries several free, key-less IP geolocation services in order until one
answers. HTTPS providers go first because plain-HTTP requests are often
blocked by antivirus "web shields", corporate proxies, and some ISPs —
ip-api.com only offers HTTP on its free tier, so it's kept as a fallback
rather than the primary. Every request sends an explicit User-Agent,
since some providers reject or rate-limit the default ``python-requests``
one.

All of these are consumer-grade services: expect city-level accuracy at
best, which is exactly what the README asks for ("use the city as a
reference").
"""

from __future__ import annotations

from typing import Callable, List, Tuple

import requests

from .. import config
from ..models import IPInfo

_DEFAULT_TIMEOUT = 6
_HEADERS = {
    "User-Agent": f"{config.APP_NAME}/{config.VERSION}",
    "Accept": "application/json",
}

_IPWHO_URL = "https://ipwho.is/"
_IPINFO_URL = "https://ipinfo.io/json"
_IP_API_URL = (
    "http://ip-api.com/json/"
    "?fields=status,message,query,city,regionName,country,isp,org,as,lat,lon"
)
_IPAPI_CO_URL = "https://ipapi.co/json/"


def _get_json(url: str, timeout: float) -> dict:
    response = requests.get(url, timeout=timeout, headers=_HEADERS)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("unexpected response format")
    return data


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _from_ipwho_is(timeout: float) -> IPInfo:
    data = _get_json(_IPWHO_URL, timeout)
    if data.get("success") is False or not data.get("ip"):
        raise ValueError(data.get("message", "lookup failed"))
    connection = data.get("connection") or {}
    asn = connection.get("asn")
    return IPInfo(
        public_ip=data.get("ip"),
        city=data.get("city"),
        region=data.get("region"),
        country=data.get("country"),
        isp=connection.get("isp"),
        org=connection.get("org"),
        asn=f"AS{asn}" if asn else None,
        latitude=_to_float(data.get("latitude")),
        longitude=_to_float(data.get("longitude")),
        source="ipwho.is",
    )


def _from_ipinfo_io(timeout: float) -> IPInfo:
    data = _get_json(_IPINFO_URL, timeout)
    if data.get("bogon") or not data.get("ip"):
        raise ValueError((data.get("error") or {}).get("message", "lookup failed"))
    # "org" looks like "AS15169 Google LLC"; split it into ASN + name.
    org = data.get("org") or ""
    asn, _, name = org.partition(" ")
    if not asn.startswith("AS"):
        asn, name = None, org
    lat, _, lon = (data.get("loc") or "").partition(",")
    return IPInfo(
        public_ip=data.get("ip"),
        city=data.get("city"),
        region=data.get("region"),
        country=data.get("country"),
        isp=name or None,
        org=name or None,
        asn=asn,
        latitude=_to_float(lat),
        longitude=_to_float(lon),
        source="ipinfo.io",
    )


def _from_ip_api(timeout: float) -> IPInfo:
    data = _get_json(_IP_API_URL, timeout)
    if data.get("status") != "success":
        raise ValueError(data.get("message", "lookup failed"))
    return IPInfo(
        public_ip=data.get("query"),
        city=data.get("city"),
        region=data.get("regionName"),
        country=data.get("country"),
        isp=data.get("isp"),
        org=data.get("org"),
        asn=data.get("as"),
        latitude=_to_float(data.get("lat")),
        longitude=_to_float(data.get("lon")),
        source="ip-api.com",
    )


def _from_ipapi_co(timeout: float) -> IPInfo:
    data = _get_json(_IPAPI_CO_URL, timeout)
    if data.get("error") or not data.get("ip"):
        raise ValueError(data.get("reason", "lookup failed"))
    return IPInfo(
        public_ip=data.get("ip"),
        city=data.get("city"),
        region=data.get("region"),
        country=data.get("country_name"),
        isp=data.get("org"),
        org=data.get("org"),
        asn=data.get("asn"),
        latitude=_to_float(data.get("latitude")),
        longitude=_to_float(data.get("longitude")),
        source="ipapi.co",
    )


PROVIDERS: List[Tuple[str, Callable[[float], IPInfo]]] = [
    ("ipwho.is", _from_ipwho_is),
    ("ipinfo.io", _from_ipinfo_io),
    ("ip-api.com", _from_ip_api),
    ("ipapi.co", _from_ipapi_co),
]


def get_ip_info(timeout: float = _DEFAULT_TIMEOUT) -> IPInfo:
    """Return public IP + best-effort geolocation, trying each provider in turn."""
    failures = []
    for name, lookup in PROVIDERS:
        try:
            return lookup(timeout)
        except Exception as exc:  # network error, timeout, bad payload, etc.
            failures.append(f"{name}: {exc}")
    return IPInfo(
        public_ip=None,
        city=None,
        region=None,
        country=None,
        isp=None,
        org=None,
        asn=None,
        latitude=None,
        longitude=None,
        source=None,
        error="Unable to reach IP geolocation services. Check your internet "
              "connection, or whether a firewall/antivirus/proxy is blocking "
              "them.\n  " + "\n  ".join(failures),
    )
