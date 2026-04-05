from unittest.mock import patch

import pytest
from langgraph.checkpoint.memory import MemorySaver

from graphs.trader.graph import build_trader_graph
from graphs.trader.state import TraderState
from models.common import ScannerSignals

MOCK_NARRATIVE = "AAPL vol elevated due to earnings."
MOCK_TRADE_RECS = '[{"strategy":"calendar_spread","direction":"long_vol","legs":[],"rationale":"test","estimated_greeks":{"delta":0},"risk_reward":"test"}]'


def _make_initial_state() -> TraderState:
    return {
        "symbol": "AAPL",
        "scanner_signals": ScannerSignals(
            iv_percentile=0.85,
            skew_kurtosis=0.6,
            dealer_gamma=-0.3,
            term_structure=0.9,
            vanna=0.7,
            charm=0.4,
            composite=0.72,
        ),
        "auto_run": True,
        "confirmed_signals": None,
        "vol_analysis": None,
        "narrative_context": None,
        "narrative": "",
        "trade_recs": [],
        "job_id": "job-test",
        "checkpoints_hit": [],
        "user_inputs": {},
    }


@pytest.mark.asyncio
@patch("graphs.trader.nodes.trade_rec._call_claude", return_value=MOCK_TRADE_RECS)
@patch("graphs.trader.nodes.synthesize._call_claude", return_value=MOCK_NARRATIVE)
async def test_trader_graph_auto_run(mock_synth, mock_rec):
    """Full auto-run skips checkpoints."""
    graph = build_trader_graph(checkpointer=None)

    state = _make_initial_state()
    result = await graph.ainvoke(state)

    assert result["confirmed_signals"] is not None
    assert result["confirmed_signals"].is_valid is True
    assert result["vol_analysis"] is not None
    assert result["narrative_context"] is not None
    assert len(result["narrative"]) > 0
    assert len(result["trade_recs"]) > 0


@pytest.mark.asyncio
@patch("graphs.trader.nodes.trade_rec._call_claude", return_value=MOCK_TRADE_RECS)
@patch("graphs.trader.nodes.synthesize._call_claude", return_value=MOCK_NARRATIVE)
async def test_trader_graph_with_checkpoints(mock_synth, mock_rec):
    """Checkpoint mode pauses at vol_surface review."""
    checkpointer = MemorySaver()
    graph = build_trader_graph(checkpointer=checkpointer)

    state = _make_initial_state()
    state["auto_run"] = False

    config = {"configurable": {"thread_id": "test-thread"}}

    # First invocation should pause at checkpoint
    result = await graph.ainvoke(state, config=config)

    # Should have completed signal_confirm and vol_surface
    assert result["confirmed_signals"] is not None
    assert result["vol_analysis"] is not None

    # Resume — should continue through remaining nodes
    result = await graph.ainvoke(None, config=config)

    # After second resume, should have narrative context
    assert result["narrative_context"] is not None

    # Resume again for synthesis
    result = await graph.ainvoke(None, config=config)
    assert len(result["narrative"]) > 0

    # Final resume for trade recs
    result = await graph.ainvoke(None, config=config)
    assert len(result["trade_recs"]) > 0
