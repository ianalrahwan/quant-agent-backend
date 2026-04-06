"""Repository for pre-computed scanner results."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ScannerResult


async def upsert_scanner_result(
    session: AsyncSession,
    symbol: str,
    scores: dict,
    composite: float,
) -> None:
    """INSERT ... ON CONFLICT (symbol) DO UPDATE SET all columns."""
    stmt = insert(ScannerResult).values(
        symbol=symbol,
        scores=scores,
        composite=composite,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol"],
        set_={
            "scores": stmt.excluded.scores,
            "composite": stmt.excluded.composite,
            "created_at": datetime.now(UTC),
        },
    )
    await session.execute(stmt)
    await session.commit()


async def get_all_scanner_results(
    session: AsyncSession,
) -> list[ScannerResult]:
    """SELECT all scanner results ordered by composite score DESC."""
    result = await session.execute(select(ScannerResult).order_by(ScannerResult.composite.desc()))
    return list(result.scalars().all())


async def delete_stale_scanner_results(
    session: AsyncSession,
    max_age_seconds: int = 600,
) -> None:
    """DELETE rows where created_at < now() - max_age_seconds."""
    cutoff = datetime.now(UTC) - timedelta(seconds=max_age_seconds)
    await session.execute(delete(ScannerResult).where(ScannerResult.created_at < cutoff))
    await session.commit()
