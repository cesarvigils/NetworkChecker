from unittest.mock import MagicMock, patch

import requests

from networkchecker.checks import carrier, ip_info
from networkchecker.models import IPInfo


def _mock_response(json_data, status_ok=True):
    response = MagicMock()
    response.json.return_value = json_data
    if status_ok:
        response.raise_for_status.return_value = None
    else:
        response.raise_for_status.side_effect = requests.HTTPError("429 Too Many Requests")
    return response


def _route(responses):
    """Build a requests.get side effect that answers per provider host.

    ``responses`` maps a host substring to a payload dict, or to an
    exception to raise. Hosts not listed behave as if unreachable.
    """

    def side_effect(url, timeout, headers):
        assert "User-Agent" in headers
        for host, answer in responses.items():
            if host in url:
                if isinstance(answer, Exception):
                    raise answer
                return answer if isinstance(answer, MagicMock) else _mock_response(answer)
        raise requests.ConnectionError(f"{url} unreachable")

    return side_effect


IPWHO_PAYLOAD = {
    "ip": "203.0.113.5",
    "success": True,
    "city": "Springfield",
    "region": "Illinois",
    "country": "United States",
    "latitude": 39.8,
    "longitude": -89.6,
    "connection": {"asn": 64500, "org": "Example Org", "isp": "Example ISP"},
}

IPINFO_PAYLOAD = {
    "ip": "198.51.100.7",
    "city": "Gotham",
    "region": "New Jersey",
    "country": "US",
    "loc": "40.7357,-74.1724",
    "org": "AS64502 Gotham Broadband",
}

IP_API_PAYLOAD = {
    "status": "success",
    "query": "203.0.113.9",
    "city": "Shelbyville",
    "regionName": "Illinois",
    "country": "United States",
    "isp": "Example ISP",
    "org": "Example Org",
    "as": "AS64500 Example",
    "lat": 39.4,
    "lon": -88.8,
}

IPAPI_CO_PAYLOAD = {
    "ip": "198.51.100.9",
    "city": "Metropolis",
    "region": "New York",
    "country_name": "United States",
    "org": "Fallback ISP",
    "asn": "AS64501",
    "latitude": 40.7,
    "longitude": -74.0,
}


def test_uses_first_https_provider():
    with patch("networkchecker.checks.ip_info.requests.get", side_effect=_route({"ipwho.is": IPWHO_PAYLOAD})):
        info = ip_info.get_ip_info()

    assert info.error is None
    assert info.source == "ipwho.is"
    assert info.public_ip == "203.0.113.5"
    assert info.location == "Springfield, Illinois, United States"
    assert info.isp == "Example ISP"
    assert info.asn == "AS64500"
    assert (info.latitude, info.longitude) == (39.8, -89.6)


def test_parses_ipinfo_io_org_and_loc():
    routes = {"ipwho.is": requests.Timeout("timed out"), "ipinfo.io": IPINFO_PAYLOAD}
    with patch("networkchecker.checks.ip_info.requests.get", side_effect=_route(routes)):
        info = ip_info.get_ip_info()

    assert info.source == "ipinfo.io"
    assert info.asn == "AS64502"
    assert info.isp == "Gotham Broadband"
    assert (info.latitude, info.longitude) == (40.7357, -74.1724)


def test_falls_back_to_http_provider_when_https_ones_fail():
    routes = {
        "ipwho.is": {"success": False, "message": "Reserved range"},
        "ipinfo.io": _mock_response({}, status_ok=False),
        "ip-api.com": IP_API_PAYLOAD,
    }
    with patch("networkchecker.checks.ip_info.requests.get", side_effect=_route(routes)):
        info = ip_info.get_ip_info()

    assert info.source == "ip-api.com"
    assert info.city == "Shelbyville"


def test_last_provider_is_used_when_all_others_fail():
    routes = {"ip-api.com": {"status": "fail", "message": "private range"}, "ipapi.co": IPAPI_CO_PAYLOAD}
    with patch("networkchecker.checks.ip_info.requests.get", side_effect=_route(routes)):
        info = ip_info.get_ip_info()

    assert info.source == "ipapi.co"
    assert info.public_ip == "198.51.100.9"


def test_reports_every_provider_error_when_all_fail():
    with patch("networkchecker.checks.ip_info.requests.get", side_effect=requests.ConnectionError("offline")):
        info = ip_info.get_ip_info()

    assert info.public_ip is None
    assert "geolocation" in info.error.lower()
    for name, _ in ip_info.PROVIDERS:
        assert name in info.error


def test_location_skips_missing_parts():
    info = IPInfo(
        public_ip="203.0.113.5", city=None, region="", country="US", isp=None, org=None,
        asn=None, latitude=None, longitude=None, source="x",
    )
    assert info.location == "US"


def test_carrier_reuses_supplied_ip_info():
    supplied = IPInfo(
        public_ip="203.0.113.5", city="A", region="B", country="C", isp="Example ISP",
        org="Example Org", asn="AS64500", latitude=None, longitude=None, source="ipwho.is",
    )
    with patch("networkchecker.checks.carrier.get_ip_info") as lookup:
        info = carrier.get_carrier_info(connection_type="Wi-Fi", ip_info=supplied)

    lookup.assert_not_called()
    assert info.isp == "Example ISP"
    assert info.error is None
