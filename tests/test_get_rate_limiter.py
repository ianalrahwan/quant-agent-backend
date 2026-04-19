from unittest.mock import MagicMock

from app.dependencies import get_rate_limiter
from app.scanner.rate_limiter import RateLimiter


def test_returns_rate_limiter_from_app_state():
    request = MagicMock()
    request.app.state.rate_limiter = RateLimiter(
        redis=MagicMock(), per_ip=5, window_secs=3600, global_daily=300
    )
    result = get_rate_limiter(request)
    assert isinstance(result, RateLimiter)
