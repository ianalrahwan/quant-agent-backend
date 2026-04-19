import asyncio

import structlog

from app.scanner.engine import run_scan
from data.cache_repo import delete_stale_analyses
from data.scanner_repo import delete_stale_scanner_results, upsert_scanner_result

logger = structlog.get_logger()

REFRESH_INTERVAL = 900  # 15 min — scanner cache only; per-ticker LLM is on-demand


async def analysis_refresh_loop(app):
    session_factory = app.state.session_factory
    await asyncio.sleep(60)  # 1 min startup delay to let rate limits reset
    while True:
        try:
            logger.info("scheduler.refresh_start")
            tickers = await run_scan()
            logger.info("scheduler.scan_complete", count=len(tickers))
            async with session_factory() as session:
                for symbol, signals in tickers:
                    scores = signals.model_dump() if hasattr(signals, "model_dump") else signals
                    await upsert_scanner_result(
                        session=session,
                        symbol=symbol,
                        scores=scores,
                        composite=scores.get("composite", 0),
                    )
                await delete_stale_scanner_results(session, max_age_seconds=600)
                # Cache cleanup still happens, decoupled from any LLM call
                await delete_stale_analyses(session, max_age_seconds=3600)
            logger.info("scheduler.refresh_done", tickers=len(tickers))
        except Exception as exc:
            logger.error("scheduler.refresh_failed", error=str(exc))
        await asyncio.sleep(REFRESH_INTERVAL)
