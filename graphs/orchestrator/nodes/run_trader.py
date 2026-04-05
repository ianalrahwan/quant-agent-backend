import structlog

from graphs.orchestrator.state import OrchestratorState
from graphs.trader.graph import build_trader_graph
from graphs.trader.state import TraderState

logger = structlog.get_logger()


async def run_trader_node(state: OrchestratorState) -> dict:
    """Run the trader analysis subgraph."""
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
    }

    graph = build_trader_graph(checkpointer=None)
    result = await graph.ainvoke(trader_state)

    logger.info(
        "run_trader.done",
        symbol=state["symbol"],
        narrative_len=len(result.get("narrative", "")),
        recs=len(result.get("trade_recs", [])),
    )

    return {
        "trader_narrative": result.get("narrative", ""),
        "trader_trade_recs": result.get("trade_recs", []),
    }
