from datetime import UTC, datetime

from fastapi import HTTPException


class RateLimiter:
    """Per-IP rolling window + global daily cap, backed by Redis."""

    def __init__(self, redis, per_ip: int, window_secs: int, global_daily: int):
        self.redis = redis
        self.per_ip = per_ip
        self.window_secs = window_secs
        self.global_daily = global_daily

    async def check(self, ip: str) -> None:
        ip_key = f"rl:ip:{ip}"
        ip_count = await self.redis.incr(ip_key)
        if ip_count == 1:
            await self.redis.expire(ip_key, self.window_secs)
        if ip_count > self.per_ip:
            raise HTTPException(
                status_code=429,
                detail="Per-IP free tier limit reached. Try again later or use the password.",
            )

        today = datetime.now(UTC).strftime("%Y%m%d")
        global_key = f"rl:global:{today}"
        global_count = await self.redis.incr(global_key)
        if global_count == 1:
            await self.redis.expire(global_key, 86460)
        if global_count > self.global_daily:
            raise HTTPException(
                status_code=429,
                detail="Free tier exhausted today. Come back tomorrow or use the password.",
            )
