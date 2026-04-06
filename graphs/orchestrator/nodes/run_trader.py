import structlog

from graphs.orchestrator.state import OrchestratorState
from graphs.trader.graph import build_trader_graph
from graphs.trader.state import TraderState
from models.events import LogEvent, PhaseEvent
from sse.bus import emit

logger = structlog.get_logger()

# Map trader node names to frontend phase names
TRADER_PHASE_MAP = {
    "signal_confirm": "signal_confirm",
    "vol_surface": "vol_surface",
    "narrative_query": "narrative_sources",
    "synthesize": "synthesis",
    "trade_rec": "trade_rec",
}


async def run_trader_node(state: OrchestratorState) -> dict:
    """Run the trader analysis subgraph, publishing SSE events per node."""
    trader_state: TraderState = {
        "symbol": state["symbol"],
        "scanner_signals": state["scanner_signals"],
        "auto_run": state["auto_run"],
        "confirmed_signals": None,
        "vol_analysis": None,
        "narrative_context": None,
        "narrative": "",
        "trade_recs": [],
        "job_id": state["job_id"],
        "checkpoints_hit": [],
        "user_inputs": {},
        "logs": [],
    }

    graph = build_trader_graph(checkpointer=None)
    result = trader_state

    async for chunk in graph.astream(trader_state):
        for node_name, node_output in chunk.items():
            result = {**result, **node_output}

            # Publish log events
            for log_msg in node_output.get("logs", []):
                await emit(LogEvent(message=log_msg).to_sse())

            # Publish phase event with data
            phase = TRADER_PHASE_MAP.get(node_name)
            if phase:
                phase_data = None
                if phase == "vol_surface" and node_output.get("vol_analysis"):
                    vol = node_output["vol_analysis"]
                    phase_data = vol.model_dump() if hasattr(vol, "model_dump") else None

                await emit(
                    PhaseEvent(phase=phase, status="complete", data=phase_data).to_sse()
                )

    logger.info(
        "run_trader.done",
        symbol=state["symbol"],
        narrative_len=len(result.get("narrative", "")),
        recs=len(result.get("trade_recs", [])),
    )

    rec_count = len(result.get("trade_recs", []))

    return {
        "trader_narrative": result.get("narrative", ""),
        "trader_trade_recs": result.get("trade_recs", []),
        "logs": [
            f"Starting trader analysis for {state['symbol']}...",
            f"Trader analysis complete — {rec_count} recommendations",
        ],
    }
