from datetime import UTC, datetime

import structlog

from data.models import SourceType
from graphs.discovery.graph import build_discovery_graph
from graphs.discovery.state import DiscoveryState
from graphs.orchestrator.state import OrchestratorState

logger = structlog.get_logger()


async def run_discovery_node(state: OrchestratorState) -> dict:
    """Run the discovery subgraph for stale sources."""
    freshness = state.get("freshness")
    symbol = state["symbol"]

    stale_types = []
    if freshness:
        stale_types = [SourceType(s) for s in freshness.stale_sources]

    discovery_state: DiscoveryState = {
        "trigger_type": "manual",
        "target_tickers": [symbol],
        "source_types": stale_types if stale_types else None,
        "raw_documents": [],
        "crawl_errors": [],
        "chunks": [],
        "embeddings_stored": 0,
        "run_id": f"orch-{state['job_id']}",
        "started_at": datetime.now(UTC),
        "completed_sources": [],
    }

    graph = build_discovery_graph()
    result = await graph.ainvoke(discovery_state)

    logger.info(
        "run_discovery.done",
        symbol=symbol,
        documents=len(result.get("raw_documents", [])),
        errors=len(result.get("crawl_errors", [])),
    )

    return {"discovery_needed": False}
