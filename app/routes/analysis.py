import time
from uuid import uuid4

import structlog
from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel

from graphs.orchestrator.graph import build_orchestrator_graph
from graphs.orchestrator.state import OrchestratorState
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


async def _run_orchestrator(bus: SSEBus, state: OrchestratorState) -> None:
    """Run the orchestrator graph in the background, publishing SSE events."""
    job_id = state["job_id"]
    set_bus_context(bus, job_id)
    t0 = time.monotonic()

    try:
        graph = build_orchestrator_graph()

        async for chunk in graph.astream(state):
            for node_name, node_output in chunk.items():
                phase = ORCHESTRATOR_PHASE_MAP.get(node_name)

                # Publish log events from node output
                for log_msg in node_output.get("logs", []):
                    await emit(LogEvent(message=log_msg).to_sse())

                # Publish phase completion (skip trader — it emits its own)
                if phase is not None:
                    await emit(PhaseEvent(phase=phase, status="complete").to_sse())

        elapsed = time.monotonic() - t0
        await emit(DoneEvent(job_id=job_id, total_time=elapsed).to_sse())

        logger.info(
            "orchestrator.complete",
            job_id=job_id,
            symbol=state["symbol"],
            elapsed=f"{elapsed:.1f}s",
        )
    except Exception as exc:
        await emit(ErrorEvent(error=str(exc)).to_sse())
        logger.error(
            "orchestrator.failed",
            job_id=job_id,
            error=str(exc),
        )


@router.post("/analyze/{symbol}")
async def analyze(
    symbol: str,
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
) -> JobResponse:
    """Kick off the full orchestrator graph for a symbol."""
    job_id = f"job-{uuid4().hex[:12]}"
    bus: SSEBus = http_request.app.state.sse_bus

    state: OrchestratorState = {
        "symbol": symbol.upper(),
        "scanner_signals": request.scanner_signals,
        "auto_run": request.auto_run,
        "freshness": None,
        "discovery_needed": False,
        "trader_narrative": "",
        "trader_trade_recs": [],
        "job_id": job_id,
        "logs": [],
    }

    background_tasks.add_task(_run_orchestrator, bus, state)

    return JobResponse(job_id=job_id)
