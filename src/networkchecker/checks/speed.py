"""Download/upload speed testing via the speedtest.net infrastructure.

Uses the ``speedtest-cli`` PyPI package (imported as ``speedtest``), a
pure-Python client with no compiled dependencies, which keeps PyInstaller
packaging simple. The import is deferred and optional so the rest of the
program works even if this dependency is missing.
"""

from __future__ import annotations

from typing import Callable, Optional

from ..models import SpeedResult


def run_speed_test(progress_callback: Optional[Callable[[str], None]] = None) -> SpeedResult:
    """Run a full download+upload speed test. Safe to call from a worker thread."""
    try:
        import speedtest
    except ImportError:
        return SpeedResult(
            download_mbps=None,
            upload_mbps=None,
            ping_ms=None,
            server_name=None,
            server_location=None,
            error=(
                "The 'speedtest-cli' package is not installed. "
                "Install it with: pip install speedtest-cli"
            ),
        )

    def notify(message: str) -> None:
        if progress_callback:
            progress_callback(message)

    try:
        notify("Finding the best test server...")
        st = speedtest.Speedtest()
        st.get_best_server()

        notify("Testing download speed...")
        download_bps = st.download()

        notify("Testing upload speed...")
        upload_bps = st.upload()

        server = st.results.server
        return SpeedResult(
            download_mbps=round(download_bps / 1_000_000, 2),
            upload_mbps=round(upload_bps / 1_000_000, 2),
            ping_ms=round(st.results.ping, 2),
            server_name=server.get("sponsor"),
            server_location=f"{server.get('name')}, {server.get('country')}",
        )
    except Exception as exc:
        return SpeedResult(
            download_mbps=None,
            upload_mbps=None,
            ping_ms=None,
            server_name=None,
            server_location=None,
            error=f"Speed test failed: {exc}",
        )
