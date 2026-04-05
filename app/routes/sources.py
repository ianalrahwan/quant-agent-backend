from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/sources/{symbol}/summary")
async def sources_summary(symbol: str) -> dict[str, Any]:
    """Return indexed source summary for a ticker.

    Stub: returns empty source data. Will query the database
    once the discovery graph populates it (Plan 2).
    """
    return {
        "symbol": symbol.upper(),
        "sources": {
            "earnings": {"last_updated": None, "count": 0},
            "news": {"last_updated": None, "count": 0},
            "podcast": {"last_updated": None, "count": 0},
            "cftc": {"last_updated": None, "count": 0},
        },
    }
