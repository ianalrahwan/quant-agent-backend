import time
from typing import Literal
from uuid import uuid4

import structlog
from fastapi import BackgroundTasks, Depends, Request
from fastapi.routing import APIRouter
from pydantic import BaseModel

from app.dependencies import get_client_ip, get_rate_limiter, get_tier
from app.scanner.rate_limiter import RateLimiter
from data.cache_repo import upsert_cached_analysis
from graphs.free.graph import build_free_graph
from graphs.orchestrator.graph import build_orchestrator_graph
from models.common import JobResponse, ScannerSignals
from models.events import DoneEvent, ErrorEvent, LogEvent, PhaseEvent
from sse.bus import SSEBus, emit, set_bus_context

logger = structlog.get_logger()

router = APIRouter()

# Map orchestrator node names to frontend phase names
ORCHESTRATOR_PHASE_MAP = {
    "check_freshness": "freshness_check",
    "run_discovery": "discovery",
    "run_trader": None,  # trader publishes its own sub-phases
}


class AnalyzeRequest(BaseModel):
    scanner_signals: ScannerSignals
    auto_run: bool = False


async def _run_graph(
    bus: SSEBus,
    state: dict,
    graph_builder,
    tier: Literal["free", "pro"],
    session_factory=None,
) -> None:
    """Run the given graph in the background, publishing SSE events."""
    job_id = state["job_id"]
    set_bus_context(bus, job_id)
    t0 = time.monotonic()

    try:
        graph = graph_builder()
        result = state

        async for chunk in graph.astream(state):
            for node_name, node_output in chunk.items():
                result = {**result, **node_output}
                phase = (
                    ORCHESTRATOR_PHASE_MAP.get(node_name, node_name)
                    if tier == "pro"
                    else node_name
                )

                # Publish log events from node output
                for log_msg in node_output.get("logs", []):
                    await emit(LogEvent(message=log_msg).to_sse())

                # Publish phase completion
                if phase is not None:
                    await emit(PhaseEvent(phase=phase, status="complete").to_sse())

        elapsed = time.monotonic() - t0

        # Write cache BEFORE emitting DoneEvent so frontend can fetch immediately
        if session_factory is not None:
            try:
                async with session_factory() as session:
                    # free graph stores "narrative"; pro orchestrator stores "trader_narrative"
                    narrative = result.get("narrative", "") or result.get("trader_narrative", "")
                    trade_recs = (
                        [
                            r.model_dump() if hasattr(r, "model_dump") else r
                            for r in result.get("trader_trade_recs", [])
                        ]
                        if tier == "pro"
                        else []
                    )
                    await upsert_cached_analysis(
                        session=session,
                        symbol=state["symbol"],
                        scanner_signals=state["scanner_signals"].model_dump()
                        if hasattr(state["scanner_signals"], "model_dump")
                        else state["scanner_signals"],
                        narrative=narrative,
                        trade_recs=trade_recs,
                        vol_surface=None,
                        phases_log=result.get("logs", []),
                        total_time=elapsed,
                        tier=tier,
                    )
            except Exception as cache_exc:
                logger.warning("analyze.cache_write_failed", error=str(cache_exc))

        await emit(DoneEvent(job_id=job_id, total_time=elapsed).to_sse())

        logger.info(
            "analyze.complete",
            job_id=job_id,
            symbol=state["symbol"],
            tier=tier,
            elapsed=f"{elapsed:.1f}s",
        )
    except Exception as exc:
        await emit(ErrorEvent(error=str(exc)).to_sse())
        logger.error("analyze.failed", job_id=job_id, error=str(exc))


@router.post("/analyze/{symbol}")
async def analyze(
    symbol: str,
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    tier: Literal["free", "pro"] = Depends(get_tier),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> JobResponse:
    """Kick off the appropriate graph based on tier."""
    if tier == "free":
        await rate_limiter.check(get_client_ip(http_request))
        graph_builder = build_free_graph
    else:
        graph_builder = build_orchestrator_graph

    job_id = f"job-{uuid4().hex[:12]}"
    bus: SSEBus = http_request.app.state.sse_bus

    state: dict = {
        "symbol": symbol.upper(),
        "scanner_signals": request.scanner_signals,
        "auto_run": request.auto_run,
        "freshness": None,
        "discovery_needed": False,
        "trader_narrative": "",
        "trader_trade_recs": [],
        "narrative": "",
        "vol_analysis": None,
        "job_id": job_id,
        "logs": [],
    }

    session_factory = getattr(http_request.app.state, "session_factory", None)
    background_tasks.add_task(_run_graph, bus, state, graph_builder, tier, session_factory)

    return JobResponse(job_id=job_id)
