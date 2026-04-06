from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import Settings
from app.logging import setup_logging
from app.routes import analysis, discovery, health, sources, stream
from sse.bus import InMemorySSEBus


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    if not hasattr(app.state, "sse_bus"):
        app.state.sse_bus = InMemorySSEBus()

    # Ensure pgvector extension is available
    settings = Settings()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    await engine.dispose()

    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Quant Agent Backend",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(analysis.router)
    app.include_router(discovery.router)
    app.include_router(stream.router)
    app.include_router(sources.router)

    return app


app = create_app()
