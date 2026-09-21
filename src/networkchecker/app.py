"""Facade that ties every check together into one "full report".

Both the CLI's ``full`` command and the GUI's "Run Full Check" button call
:func:`run_full_report`. Each check is isolated so that one failure (say,
no internet for the IP lookup) never stops the others from running.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from .checks.carrier import get_carrier_info
from .checks.ip_info import get_ip_info
from .checks.packet_loss import packet_loss_test
from .checks.ping import ping_host
from .checks.ssid import get_ssid_info
from .checks.speed import run_speed_test
from .models import FullReport
from .utils.platform_utils import detect_connection_type

ProgressCallback = Optional[Callable[[str], None]]


def run_full_report(include_speed_test: bool = True, progress_callback: ProgressCallback = None) -> FullReport:
    """Run every check and return a combined :class:`FullReport`.

    ``include_speed_test`` is a separate flag because a speed test takes
    much longer (tens of seconds, real bandwidth used) than every other
    check combined.
    """

    def notify(message: str) -> None:
        if progress_callback:
            progress_callback(message)

    notify("Checking Wi-Fi / SSID...")
    ssid = get_ssid_info()

    notify("Running ping test...")
    ping = ping_host()

    notify("Running packet loss test...")
    loss = packet_loss_test()

    notify("Looking up public IP and location...")
    ip_info = get_ip_info()

    notify("Looking up ISP / carrier info...")
    connection_type = detect_connection_type()
    carrier = get_carrier_info(connection_type=connection_type)

    speed = None
    if include_speed_test:
        speed = run_speed_test(progress_callback=progress_callback)

    notify("Done.")
    return FullReport(
        generated_at=datetime.utcnow(),
        ssid=ssid,
        ping=ping,
        packet_loss=loss,
        ip_info=ip_info,
        carrier=carrier,
        speed=speed,
    )
