import asyncio
import time
from uuid import uuid4

import structlog

from app.scanner.engine import run_scan
from data.cache_repo import delete_stale_analyses, upsert_cached_analysis
from graphs.orchestrator.graph import build_orchestrator_graph
from graphs.orchestrator.state import OrchestratorState
from sse.bus import set_bus_context

logger = structlog.get_logger()

REFRESH_INTERVAL = 300


async def _run_for_ticker(app, symbol, signals, session_factory):
    job_id = f"cache-{uuid4().hex[:8]}"
    bus = app.state.sse_bus
    set_bus_context(bus, job_id)

    state: OrchestratorState = {
        "symbol": symbol,
        "scanner_signals": signals,
        "auto_run": True,
        "freshness": None,
        "discovery_needed": False,
        "trader_narrative": "",
        "trader_trade_recs": [],
        "job_id": job_id,
        "logs": [],
    }

    t0 = time.monotonic()
    try:
        graph = build_orchestrator_graph()
        result = state
        async for chunk in graph.astream(state):
            for _node, output in chunk.items():
                result = {**result, **output}

        elapsed = time.monotonic() - t0
        async with session_factory() as session:
            await upsert_cached_analysis(
                session=session,
                symbol=symbol,
                scanner_signals=signals.model_dump() if hasattr(signals, "model_dump") else signals,
                narrative=result.get("trader_narrative", ""),
                trade_recs=[
                    r.model_dump() if hasattr(r, "model_dump") else r
                    for r in result.get("trader_trade_recs", [])
                ],
                vol_surface=None,
                phases_log=result.get("logs", []),
                total_time=elapsed,
            )
        logger.info("scheduler.ticker_complete", symbol=symbol, elapsed=f"{elapsed:.1f}s")
    except Exception as exc:
        logger.error("scheduler.ticker_failed", symbol=symbol, error=str(exc))


async def analysis_refresh_loop(app):
    session_factory = app.state.session_factory
    await asyncio.sleep(10)
    while True:
        try:
            logger.info("scheduler.refresh_start")
            tickers = await run_scan()
            logger.info("scheduler.scan_complete", count=len(tickers))
            for symbol, signals in tickers[:10]:
                await _run_for_ticker(app, symbol, signals, session_factory)
            async with session_factory() as session:
                await delete_stale_analyses(session, max_age_seconds=3600)
            logger.info("scheduler.refresh_done", tickers=len(tickers))
        except Exception as exc:
            logger.error("scheduler.refresh_failed", error=str(exc))
        await asyncio.sleep(REFRESH_INTERVAL)
