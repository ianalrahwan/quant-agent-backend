from unittest.mock import MagicMock

from app.dependencies import get_client_ip


def _make_request(headers: dict, client_host: str = "127.0.0.1") -> MagicMock:
    req = MagicMock()
    req.headers = headers
    req.client = MagicMock()
    req.client.host = client_host
    return req


def test_uses_x_forwarded_for_first_entry():
    req = _make_request({"X-Forwarded-For": "203.0.113.5, 10.0.0.1"})
    assert get_client_ip(req) == "203.0.113.5"


def test_falls_back_to_request_client_host():
    req = _make_request({}, client_host="192.0.2.42")
    assert get_client_ip(req) == "192.0.2.42"


def test_handles_missing_client():
    req = MagicMock()
    req.headers = {}
    req.client = None
    assert get_client_ip(req) == "0.0.0.0"
