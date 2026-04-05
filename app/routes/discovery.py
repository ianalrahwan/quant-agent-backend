from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class DiscoverRequest(BaseModel):
    target_tickers: list[str] | None = None
    source_types: list[str] | None = None


class DiscoverResponse(BaseModel):
    run_id: str


@router.post("/discover")
async def discover(request: DiscoverRequest) -> DiscoverResponse:
    """Manually trigger the resource discovery graph.

    Stub: creates a run ID but does not execute the graph yet.
    Will be wired in Plan 2.
    """
    run_id = f"discovery-{uuid4().hex[:12]}"
    return DiscoverResponse(run_id=run_id)
