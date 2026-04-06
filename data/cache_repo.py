"""Repository for cached analysis CRUD operations."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CachedAnalysis


async def upsert_cached_analysis(
    session: AsyncSession,
    symbol: str,
    scanner_signals: dict,
    narrative: str,
    trade_recs: list,
    vol_surface: dict | None,
    phases_log: list,
    total_time: float | None,
) -> None:
    """INSERT ... ON CONFLICT (symbol) DO UPDATE SET all columns."""
    stmt = insert(CachedAnalysis).values(
        symbol=symbol,
        scanner_signals=scanner_signals,
        narrative=narrative,
        trade_recs=trade_recs,
        vol_surface=vol_surface,
        phases_log=phases_log,
        total_time=total_time,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol"],
        set_={
            "scanner_signals": stmt.excluded.scanner_signals,
            "narrative": stmt.excluded.narrative,
            "trade_recs": stmt.excluded.trade_recs,
            "vol_surface": stmt.excluded.vol_surface,
            "phases_log": stmt.excluded.phases_log,
            "total_time": stmt.excluded.total_time,
            "created_at": datetime.now(UTC),
        },
    )
    await session.execute(stmt)
    await session.commit()


async def get_cached_analysis(
    session: AsyncSession,
    symbol: str,
) -> CachedAnalysis | None:
    """SELECT cached analysis by symbol."""
    result = await session.execute(select(CachedAnalysis).where(CachedAnalysis.symbol == symbol))
    return result.scalar_one_or_none()


async def delete_stale_analyses(
    session: AsyncSession,
    max_age_seconds: int = 3600,
) -> None:
    """DELETE rows where created_at < now() - max_age_seconds."""
    cutoff = datetime.now(UTC) - timedelta(seconds=max_age_seconds)
    await session.execute(delete(CachedAnalysis).where(CachedAnalysis.created_at < cutoff))
    await session.commit()
