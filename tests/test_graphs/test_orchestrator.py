from unittest.mock import patch

import pytest
import respx
from httpx import Response

from graphs.orchestrator.graph import build_orchestrator_graph
from graphs.orchestrator.state import OrchestratorState
from models.common import ScannerSignals

MOCK_NARRATIVE = "AAPL vol elevated."
MOCK_RECS = (
    '[{"strategy":"calendar_spread","direction":"long_vol",'
    '"legs":[],"rationale":"test",'
    '"estimated_greeks":{"delta":0},"risk_reward":"test"}]'
)


def _make_state() -> OrchestratorState:
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
        "freshness": None,
        "discovery_needed": False,
        "trader_narrative": "",
        "trader_trade_recs": [],
        "job_id": "job-test",
    }


@pytest.mark.asyncio
@respx.mock
@patch("graphs.trader.nodes.trade_rec._call_claude", return_value=MOCK_RECS)
@patch("graphs.trader.nodes.synthesize._call_claude", return_value=MOCK_NARRATIVE)
async def test_orchestrator_full_run(mock_synth, mock_rec):
    """Full orchestrator: freshness check -> discovery (stale) -> trader."""
    respx.route().mock(return_value=Response(200, json=[]))
    respx.post("https://api.voyageai.com/v1/embeddings").mock(
        return_value=Response(
            200,
            json={"data": [{"embedding": [0.1] * 1024}], "usage": {"total_tokens": 1}},
        )
    )

    graph = build_orchestrator_graph()
    state = _make_state()
    result = await graph.ainvoke(state)

    assert result["freshness"] is not None
    assert result["trader_narrative"] != ""
    assert len(result["trader_trade_recs"]) > 0


@pytest.mark.asyncio
@patch("graphs.trader.nodes.trade_rec._call_claude", return_value=MOCK_RECS)
@patch("graphs.trader.nodes.synthesize._call_claude", return_value=MOCK_NARRATIVE)
@patch("graphs.orchestrator.nodes.check_freshness.is_stale", return_value=False)
async def test_orchestrator_skips_discovery_when_fresh(mock_stale, mock_synth, mock_rec):
    """When all sources are fresh, skip discovery and go straight to trader."""
    graph = build_orchestrator_graph()
    state = _make_state()
    result = await graph.ainvoke(state)

    assert result["freshness"] is not None
    assert result["freshness"].all_fresh is True
    assert result["discovery_needed"] is False
    assert len(result["trader_trade_recs"]) > 0
