"""Full Network Checker Interface.

A cross-platform network diagnostics toolkit: SSID lookup, ping/latency
rating, packet loss testing, public IP + geolocation, ISP/carrier info,
download/upload speed testing, and an optional background stability
scanner with weekly summaries.
"""

from .config import APP_NAME, VERSION

__all__ = ["APP_NAME", "VERSION"]
__version__ = VERSION
