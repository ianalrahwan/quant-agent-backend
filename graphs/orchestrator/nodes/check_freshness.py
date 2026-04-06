import structlog

from data.models import SourceType
from graphs.discovery.schedule import is_stale
from graphs.orchestrator.state import FreshnessReport, OrchestratorState

logger = structlog.get_logger()

ALL_SOURCES = [SourceType.EARNINGS, SourceType.NEWS, SourceType.PODCAST, SourceType.CFTC]


async def check_freshness_node(state: OrchestratorState) -> dict:
    """Check which data sources are stale for this ticker.

    In production, queries the source_runs table for last crawl timestamps.
    Without a DB session, assumes all sources are stale (never crawled).
    """
    symbol = state["symbol"]
    stale: list[str] = []
    fresh: list[str] = []

    for source_type in ALL_SOURCES:
        last_run = None
        if is_stale(source_type, last_run):
            stale.append(source_type.value)
        else:
            fresh.append(source_type.value)

    all_fresh = len(stale) == 0
    report = FreshnessReport(
        stale_sources=stale,
        fresh_sources=fresh,
        all_fresh=all_fresh,
    )

    logger.info("check_freshness.done", symbol=symbol, stale=stale, fresh=fresh)

    if all_fresh:
        log_msg = f"All sources fresh for {symbol}"
    else:
        log_msg = f"Sources stale for {symbol}: {', '.join(stale)}"

    return {
        "freshness": report,
        "discovery_needed": not all_fresh,
        "logs": [f"Checking source freshness for {symbol}...", log_msg],
    }
