from datetime import datetime

from networkchecker.models import SSIDInfo, result_to_dict


def test_result_to_dict_stringifies_datetimes():
    info = SSIDInfo(
        ssid="Home", signal_percent=90, link_speed_mbps=866.0,
        connected_since=datetime(2026, 1, 1, 12, 0, 0), interface_name="wlan0",
        supported=True, error=None,
    )
    data = result_to_dict(info)
    assert data["connected_since"] == "2026-01-01T12:00:00"
    assert data["ssid"] == "Home"
