from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from data.scanner_repo import get_all_scanner_results

router = APIRouter()


@router.get("/scanner")
async def get_scanner(session: AsyncSession = Depends(get_session)):
    results = await get_all_scanner_results(session)
    return [
        {
            "symbol": r.symbol,
            "scores": r.scores,
            "composite": r.composite,
            "created_at": r.created_at.isoformat(),
        }
        for r in results
    ]
