"""ISP / carrier information.

For Wi-Fi and Ethernet connections, "carrier" data is really ISP data,
which is best obtained from the reverse-IP/WHOIS-style fields a
geolocation lookup already returns (isp/org/asn) — so this module reuses
:mod:`networkchecker.checks.ip_info`. On Windows, if a mobile broadband
(cellular) adapter is present, ``netsh mbn show interfaces`` additionally
exposes the actual mobile carrier/provider name.
"""

from __future__ import annotations

import platform
import re
import subprocess
from typing import Optional

from ..models import CarrierInfo
from .ip_info import get_ip_info


def _windows_mobile_carrier() -> Optional[str]:
    try:
        result = subprocess.run(
            ["netsh", "mbn", "show", "interfaces"],
            capture_output=True,
            text=True,
            timeout=6,
            encoding="utf-8",
            errors="replace",
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    match = re.search(r"^\s*Provider\s*:\s*(.+)$", result.stdout, re.MULTILINE)
    return match.group(1).strip() if match else None


def get_carrier_info(connection_type: str = "Unknown") -> CarrierInfo:
    """Return ISP/ASN info from IP geolocation, plus mobile carrier on Windows."""
    ip_info = get_ip_info()

    mobile_carrier = None
    if platform.system() == "Windows":
        mobile_carrier = _windows_mobile_carrier()

    if ip_info.error:
        return CarrierInfo(
            connection_type=connection_type,
            mobile_carrier=mobile_carrier,
            error=ip_info.error,
        )

    return CarrierInfo(
        isp=ip_info.isp,
        organization=ip_info.org,
        asn=ip_info.asn,
        connection_type=connection_type,
        mobile_carrier=mobile_carrier,
    )
