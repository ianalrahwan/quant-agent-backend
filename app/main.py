import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import Settings
from app.logging import setup_logging
from app.routes import analysis, cached, discovery, health, sources, stream
from app.scheduler import analysis_refresh_loop
from db.session import create_session_factory
from sse.bus import InMemorySSEBus


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

    from alembic.config import Config

    from alembic import command

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    app.state.session_factory = create_session_factory(settings.effective_database_url)

    refresh_task = asyncio.create_task(analysis_refresh_loop(app))

    yield

    refresh_task.cancel()


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

    return app


app = create_app()
