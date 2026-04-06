from datetime import UTC, datetime

import structlog

from data.models import SourceType
from graphs.discovery.graph import build_discovery_graph
from graphs.discovery.state import DiscoveryState
from graphs.orchestrator.state import OrchestratorState
from models.events import LogEvent, PhaseEvent
from sse.bus import emit

logger = structlog.get_logger()

# Map discovery node names to frontend phase names
DISCOVERY_PHASE_MAP = {
    "crawl_earnings": "crawl_earnings",
    "crawl_news": "crawl_news",
    "crawl_podcasts": "crawl_podcasts",
    "crawl_cftc": "crawl_cftc",
    "chunk_embed": "chunk_embed",
    "index": "index",
}


async def run_discovery_node(state: OrchestratorState) -> dict:
    """Run the discovery subgraph for stale sources, publishing SSE events per node."""
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
        "logs": [],
    }

    graph = build_discovery_graph()
    result = discovery_state

    async for chunk in graph.astream(discovery_state):
        for node_name, node_output in chunk.items():
            result = {**result, **node_output}

            # Publish log events
            for log_msg in node_output.get("logs", []):
                await emit(LogEvent(message=log_msg).to_sse())

            # Publish phase event
            phase = DISCOVERY_PHASE_MAP.get(node_name)
            if phase:
                await emit(PhaseEvent(phase=phase, status="complete").to_sse())

    logger.info(
        "run_discovery.done",
        symbol=symbol,
        documents=len(result.get("raw_documents", [])),
        errors=len(result.get("crawl_errors", [])),
    )

    doc_count = len(result.get("raw_documents", []))
    error_count = len(result.get("crawl_errors", []))

    logs = [f"Running discovery for {symbol}..."]
    if doc_count > 0:
        logs.append(f"Discovery complete — {doc_count} documents indexed")
    if error_count > 0:
        logs.append(f"Discovery had {error_count} source errors (partial success)")

    return {"discovery_needed": False, "logs": logs}
