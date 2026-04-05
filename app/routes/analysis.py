from uuid import uuid4

import structlog
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from graphs.trader.graph import build_trader_graph
from graphs.trader.state import TraderState
from models.common import JobResponse, ScannerSignals

logger = structlog.get_logger()

router = APIRouter()


class AnalyzeRequest(BaseModel):
    scanner_signals: ScannerSignals
    auto_run: bool = False


async def _run_trader(state: TraderState) -> None:
    """Run the trader graph in the background."""
    try:
        graph = build_trader_graph(checkpointer=None)
        result = await graph.ainvoke(state)
        logger.info(
            "trader.complete",
            job_id=state["job_id"],
            symbol=state["symbol"],
            recs=len(result.get("trade_recs", [])),
        )
    except Exception as exc:
        logger.error(
            "trader.failed",
            job_id=state["job_id"],
            error=str(exc),
        )


@router.post("/analyze/{symbol}")
async def analyze(
    symbol: str,
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
) -> JobResponse:
    """Kick off the trader analysis graph for a symbol."""
    job_id = f"job-{uuid4().hex[:12]}"

    state: TraderState = {
        "symbol": symbol.upper(),
        "scanner_signals": request.scanner_signals,
        "auto_run": request.auto_run,
        "confirmed_signals": None,
        "vol_analysis": None,
        "narrative_context": None,
        "narrative": "",
        "trade_recs": [],
        "job_id": job_id,
        "checkpoints_hit": [],
        "user_inputs": {},
    }

    background_tasks.add_task(_run_trader, state)

    return JobResponse(job_id=job_id)
