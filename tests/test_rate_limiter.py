from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException


def _fake_redis(state: dict):
    """A tiny in-memory fake matching the Redis methods we use."""
    redis = AsyncMock()

    async def incr(key: str) -> int:
        state[key] = state.get(key, 0) + 1
        return state[key]

    async def expire(key: str, secs: int) -> bool:
        return True

    redis.incr = AsyncMock(side_effect=incr)
    redis.expire = AsyncMock(side_effect=expire)
    return redis


@pytest.mark.asyncio
async def test_per_ip_limit_enforced():
    from app.scanner.rate_limiter import RateLimiter

    state: dict = {}
    rl = RateLimiter(redis=_fake_redis(state), per_ip=2, window_secs=60, global_daily=1000)
    await rl.check("1.1.1.1")
    await rl.check("1.1.1.1")
    with pytest.raises(HTTPException) as exc:
        await rl.check("1.1.1.1")
    assert exc.value.status_code == 429
    assert "Per-IP" in exc.value.detail


@pytest.mark.asyncio
async def test_global_limit_enforced():
    from app.scanner.rate_limiter import RateLimiter

    state: dict = {}
    rl = RateLimiter(redis=_fake_redis(state), per_ip=100, window_secs=60, global_daily=2)
    await rl.check("1.1.1.1")
    await rl.check("2.2.2.2")
    raised = False
    try:
        await rl.check("3.3.3.3")
    except HTTPException as exc:
        assert exc.status_code == 429
        assert "exhausted" in exc.detail.lower()
        raised = True
    assert raised


@pytest.mark.asyncio
async def test_separate_ips_count_separately_for_per_ip():
    from app.scanner.rate_limiter import RateLimiter

    state: dict = {}
    rl = RateLimiter(redis=_fake_redis(state), per_ip=1, window_secs=60, global_daily=1000)
    await rl.check("1.1.1.1")  # first call from this IP
    await rl.check("2.2.2.2")  # different IP, fresh limit
    with pytest.raises(HTTPException):
        await rl.check("1.1.1.1")
