import asyncio
from datetime import datetime
from uuid import uuid4

import structlog
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from data.models import SourceType
from graphs.discovery.graph import build_discovery_graph
from graphs.discovery.state import DiscoveryState

logger = structlog.get_logger()

router = APIRouter()


class DiscoverRequest(BaseModel):
    target_tickers: list[str] | None = None
    source_types: list[str] | None = None


class DiscoverResponse(BaseModel):
    run_id: str


async def _run_discovery(state: DiscoveryState) -> None:
    """Run the discovery graph in the background."""
    try:
        graph = build_discovery_graph()
        result = await graph.ainvoke(state)
        logger.info(
            "discovery.complete",
            run_id=state["run_id"],
            documents=len(result.get("raw_documents", [])),
            errors=len(result.get("crawl_errors", [])),
        )
    except Exception as exc:
        logger.error("discovery.failed", run_id=state["run_id"], error=str(exc))


@router.post("/discover")
async def discover(
    request: DiscoverRequest,
    background_tasks: BackgroundTasks,
) -> DiscoverResponse:
    """Trigger the resource discovery graph."""
    run_id = f"discovery-{uuid4().hex[:12]}"

    source_types = (
        [SourceType(s) for s in request.source_types] if request.source_types else None
    )

    state: DiscoveryState = {
        "trigger_type": "manual",
        "target_tickers": request.target_tickers,
        "source_types": source_types,
        "raw_documents": [],
        "crawl_errors": [],
        "chunks": [],
        "embeddings_stored": 0,
        "run_id": run_id,
        "started_at": datetime.utcnow(),
        "completed_sources": [],
    }

    background_tasks.add_task(_run_discovery, state)

    return DiscoverResponse(run_id=run_id)
