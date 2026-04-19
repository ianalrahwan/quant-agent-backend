import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import Settings
from app.logging import setup_logging
from app.routes import analysis, cached, discovery, health, scanner, sources, stream
from app.scanner.rate_limiter import RateLimiter
from app.scheduler import analysis_refresh_loop
from db.session import create_session_factory
from sse.bus import InMemorySSEBus


def _run_alembic_upgrade(db_url: str) -> None:
    """Run Alembic upgrade in a sync context (called from a thread)."""
    from alembic.config import Config

    from alembic import command

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    if not hasattr(app.state, "sse_bus"):
        app.state.sse_bus = InMemorySSEBus()

    # Run migrations and ensure pgvector extension
    settings = Settings()
    engine = create_async_engine(settings.effective_database_url)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    await engine.dispose()

    # Run Alembic in a thread so asyncio.run() inside env.py works
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, partial(_run_alembic_upgrade, settings.effective_database_url))

    app.state.session_factory = create_session_factory(settings.effective_database_url)

    redis_client = AsyncRedis.from_url(settings.redis_url, decode_responses=True)
    app.state.redis = redis_client
    app.state.rate_limiter = RateLimiter(
        redis=redis_client,
        per_ip=settings.rate_limit_per_ip,
        window_secs=settings.rate_limit_window_secs,
        global_daily=settings.rate_limit_global_daily,
    )

    refresh_task = asyncio.create_task(analysis_refresh_loop(app))

    try:
        yield
    finally:
        refresh_task.cancel()
        await redis_client.aclose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Quant Agent Backend",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=Settings().cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(analysis.router)
    app.include_router(discovery.router)
    app.include_router(stream.router)
    app.include_router(sources.router)
    app.include_router(cached.router)
    app.include_router(scanner.router)

    return app


app = create_app()
