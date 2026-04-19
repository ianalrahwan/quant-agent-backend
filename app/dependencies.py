import secrets
from collections.abc import AsyncGenerator
from typing import Literal

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.scanner.rate_limiter import RateLimiter

_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def override_settings(settings: Settings) -> None:
    """Override settings for testing."""
    global _settings
    _settings = settings


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session from the app-level factory."""
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        yield session


def get_tier(request: Request) -> Literal["free", "pro"]:
    """Return 'pro' iff request has a valid X-Pro-Token header. Never raises."""
    settings = get_settings()
    expected = settings.pro_tier_token
    if not expected:
        return "free"
    try:
        provided = request.headers.get("X-Pro-Token", "") if request.headers else ""
    except Exception:
        return "free"
    if not provided:
        return "free"
    if secrets.compare_digest(provided, expected):
        return "pro"
    return "free"


def get_client_ip(request: Request) -> str:
    """Return the originating client IP, preferring X-Forwarded-For."""
    xff = request.headers.get("X-Forwarded-For", "") if request.headers else ""
    if xff:
        return xff.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "0.0.0.0"


def get_rate_limiter(request: Request) -> RateLimiter:
    """Return the singleton RateLimiter from app state."""
    return request.app.state.rate_limiter
