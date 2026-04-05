from uuid import uuid4

import structlog
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from graphs.orchestrator.graph import build_orchestrator_graph
from graphs.orchestrator.state import OrchestratorState
from models.common import JobResponse, ScannerSignals

logger = structlog.get_logger()

router = APIRouter()


class AnalyzeRequest(BaseModel):
    scanner_signals: ScannerSignals
    auto_run: bool = False


async def _run_orchestrator(state: OrchestratorState) -> None:
    """Run the orchestrator graph in the background."""
    try:
        graph = build_orchestrator_graph()
        result = await graph.ainvoke(state)
        logger.info(
            "orchestrator.complete",
            job_id=state["job_id"],
            symbol=state["symbol"],
            recs=len(result.get("trader_trade_recs", [])),
        )
    except Exception as exc:
        logger.error(
            "orchestrator.failed",
            job_id=state["job_id"],
            error=str(exc),
        )


@router.post("/analyze/{symbol}")
async def analyze(
    symbol: str,
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
) -> JobResponse:
    """Kick off the full orchestrator graph for a symbol."""
    job_id = f"job-{uuid4().hex[:12]}"

    state: OrchestratorState = {
        "symbol": symbol.upper(),
        "scanner_signals": request.scanner_signals,
        "auto_run": request.auto_run,
        "freshness": None,
        "discovery_needed": False,
        "trader_narrative": "",
        "trader_trade_recs": [],
        "job_id": job_id,
    }

    background_tasks.add_task(_run_orchestrator, state)

    return JobResponse(job_id=job_id)
