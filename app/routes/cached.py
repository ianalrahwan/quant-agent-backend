from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from data.cache_repo import get_cached_analysis

router = APIRouter()


@router.get("/cached/{symbol}")
async def get_cached(symbol: str, session: AsyncSession = Depends(get_session)):
    result = await get_cached_analysis(session, symbol.upper())
    if result is None:
        raise HTTPException(status_code=404, detail="No cached analysis")
    return {
        "symbol": result.symbol,
        "scanner_signals": result.scanner_signals,
        "narrative": result.narrative,
        "trade_recs": result.trade_recs,
        "vol_surface": result.vol_surface,
        "phases_log": result.phases_log,
        "total_time": result.total_time,
        "created_at": result.created_at.isoformat(),
    }
