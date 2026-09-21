from unittest.mock import MagicMock, patch

import pytest
import requests

from networkchecker.checks import ip_info


def _mock_response(json_data, status_ok=True):
    response = MagicMock()
    response.json.return_value = json_data
    if status_ok:
        response.raise_for_status.return_value = None
    else:
        response.raise_for_status.side_effect = requests.HTTPError("bad status")
    return response


def test_get_ip_info_uses_primary_provider():
    payload = {
        "status": "success",
        "query": "203.0.113.5",
        "city": "Springfield",
        "regionName": "Illinois",
        "country": "United States",
        "isp": "Example ISP",
        "org": "Example Org",
        "as": "AS64500 Example",
        "lat": 39.8,
        "lon": -89.6,
    }
    with patch("networkchecker.checks.ip_info.requests.get", return_value=_mock_response(payload)):
        info = ip_info.get_ip_info()

    assert info.public_ip == "203.0.113.5"
    assert info.city == "Springfield"
    assert info.source == "ip-api.com"
    assert info.error is None


def test_get_ip_info_falls_back_when_primary_fails():
    fallback_payload = {
        "ip": "198.51.100.9",
        "city": "Metropolis",
        "region": "New York",
        "country_name": "United States",
        "org": "Fallback ISP",
        "asn": "AS64501",
        "latitude": 40.7,
        "longitude": -74.0,
    }

    def side_effect(url, timeout):
        if "ip-api.com" in url:
            raise requests.ConnectionError("primary down")
        return _mock_response(fallback_payload)

    with patch("networkchecker.checks.ip_info.requests.get", side_effect=side_effect):
        info = ip_info.get_ip_info()

    assert info.public_ip == "198.51.100.9"
    assert info.source == "ipapi.co"
    assert info.error is None


def test_get_ip_info_reports_error_when_both_providers_fail():
    with patch("networkchecker.checks.ip_info.requests.get", side_effect=requests.ConnectionError("offline")):
        info = ip_info.get_ip_info()

    assert info.public_ip is None
    assert info.error is not None
    assert "geolocation" in info.error.lower()


def test_get_ip_info_handles_primary_status_failure_payload():
    payload = {"status": "fail", "message": "private range"}
    with patch("networkchecker.checks.ip_info.requests.get") as get_mock:
        get_mock.side_effect = [
            _mock_response(payload),
            _mock_response({
                "ip": "198.51.100.9", "city": "X", "region": "Y", "country_name": "Z",
                "org": "O", "asn": "AS1", "latitude": 0, "longitude": 0,
            }),
        ]
        info = ip_info.get_ip_info()

    assert info.source == "ipapi.co"
