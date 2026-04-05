from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

from models.common import ScannerSignals, JobResponse

router = APIRouter()


class AnalyzeRequest(BaseModel):
    scanner_signals: ScannerSignals
    auto_run: bool = False


@router.post("/analyze/{symbol}")
async def analyze(symbol: str, request: AnalyzeRequest) -> JobResponse:
    """Kick off the orchestrator graph for a symbol.

    Stub: creates a job ID but does not run the graph yet.
    Graph execution will be wired in Plan 3/4.
    """
    job_id = f"job-{uuid4().hex[:12]}"
    return JobResponse(job_id=job_id)
