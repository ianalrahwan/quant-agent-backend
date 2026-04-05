from unittest.mock import patch

from graphs.orchestrator.nodes.run_trader import run_trader_node
from graphs.orchestrator.state import OrchestratorState
from models.common import ScannerSignals

MOCK_NARRATIVE = "AAPL vol elevated."
MOCK_RECS = (
    '[{"strategy":"calendar_spread","direction":"long_vol",'
    '"legs":[],"rationale":"test",'
    '"estimated_greeks":{"delta":0},"risk_reward":"test"}]'
)


@patch("graphs.trader.nodes.trade_rec._call_claude", return_value=MOCK_RECS)
@patch("graphs.trader.nodes.synthesize._call_claude", return_value=MOCK_NARRATIVE)
async def test_run_trader_invokes_graph(mock_synth, mock_rec):
    state: OrchestratorState = {
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

    result = await run_trader_node(state)

    assert len(result["trader_narrative"]) > 0
    assert len(result["trader_trade_recs"]) > 0
    assert result["trader_trade_recs"][0].strategy == "calendar_spread"
