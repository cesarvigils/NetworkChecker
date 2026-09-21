"""Public IP address and approximate geolocation.

Queries ip-api.com first (free, no API key, generous rate limit) and
falls back to ipapi.co if that fails or times out. Both are consumer-grade
IP geolocation services: expect city-level accuracy at best, which is
exactly what the README asks for ("use the city as a reference").
"""

from __future__ import annotations

import requests

from ..models import IPInfo

_PRIMARY_URL = (
    "http://ip-api.com/json/"
    "?fields=status,message,query,city,regionName,country,isp,org,as,lat,lon"
)
_FALLBACK_URL = "https://ipapi.co/json/"
_DEFAULT_TIMEOUT = 6


def _from_ip_api(timeout: float) -> IPInfo:
    response = requests.get(_PRIMARY_URL, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "success":
        raise ValueError(data.get("message", "ip-api.com lookup failed"))
    return IPInfo(
        public_ip=data.get("query"),
        city=data.get("city"),
        region=data.get("regionName"),
        country=data.get("country"),
        isp=data.get("isp"),
        org=data.get("org"),
        asn=data.get("as"),
        latitude=data.get("lat"),
        longitude=data.get("lon"),
        source="ip-api.com",
    )


def _from_ipapi_co(timeout: float) -> IPInfo:
    response = requests.get(_FALLBACK_URL, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise ValueError(data.get("reason", "ipapi.co lookup failed"))
    return IPInfo(
        public_ip=data.get("ip"),
        city=data.get("city"),
        region=data.get("region"),
        country=data.get("country_name"),
        isp=data.get("org"),
        org=data.get("org"),
        asn=data.get("asn"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        source="ipapi.co",
    )


def get_ip_info(timeout: float = _DEFAULT_TIMEOUT) -> IPInfo:
    """Return public IP + best-effort geolocation, trying two providers."""
    last_error: Exception | None = None
    for lookup in (_from_ip_api, _from_ipapi_co):
        try:
            return lookup(timeout)
        except Exception as exc:  # network error, timeout, bad payload, etc.
            last_error = exc
            continue
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
        error=f"Unable to reach IP geolocation services: {last_error}",
    )
