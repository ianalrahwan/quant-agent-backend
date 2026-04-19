from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.dependencies import get_tier, override_settings


def _make_request(headers: dict) -> MagicMock:
    req = MagicMock()
    req.headers = headers
    return req


def setup_function():
    override_settings(Settings(pro_tier_token="correct-secret"))


def test_no_header_returns_free():
    assert get_tier(_make_request({})) == "free"


def test_valid_header_returns_pro():
    assert get_tier(_make_request({"X-Pro-Token": "correct-secret"})) == "pro"


def test_wrong_header_returns_free():
    assert get_tier(_make_request({"X-Pro-Token": "wrong-secret"})) == "free"


def test_unset_token_in_settings_always_returns_free():
    override_settings(Settings(pro_tier_token=None))
    assert get_tier(_make_request({"X-Pro-Token": "anything"})) == "free"


def test_get_tier_never_raises():
    req = MagicMock()
    req.headers = None
    try:
        result = get_tier(req)
        assert result in ("free", "pro")
    except Exception as exc:
        pytest.fail(f"get_tier raised {exc!r}")
