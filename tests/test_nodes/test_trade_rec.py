import json
from unittest.mock import patch

from graphs.trader.nodes.trade_rec import trade_rec_node
from graphs.trader.state import (
    ConfirmedSignals,
    NarrativeContext,
    TraderState,
    VolSurfaceAnalysis,
)
from models.common import ScannerSignals

MOCK_CLAUDE_RESPONSE = json.dumps(
    [
        {
            "strategy": "calendar_spread",
            "direction": "long_vol",
            "legs": [
                {"action": "buy", "expiry": "2026-06-19", "strike": 200, "type": "put"},
                {"action": "sell", "expiry": "2026-05-16", "strike": 200, "type": "put"},
            ],
            "rationale": "Backwardation steepest at 30/60d. Vanna supports.",
            "estimated_greeks": {"delta": -0.05, "vega": 8.2, "theta": -0.3},
            "risk_reward": "Max loss: debit paid. Target: 50% vol expansion.",
        }
    ]
)


def _make_state() -> TraderState:
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
        "auto_run": False,
        "confirmed_signals": ConfirmedSignals(
            is_valid=True,
            iv_percentile=0.85,
            term_structure_regime="backwardation",
            dealer_gamma_regime="short",
            composite=0.72,
            summary="Strong backwardation",
        ),
        "vol_analysis": VolSurfaceAnalysis(
            term_structure={"30d": 0.28, "60d": 0.24, "90d": 0.22},
            skew={"25d_put": 0.31, "atm": 0.22, "25d_call": 0.17},
            iv_percentile=0.85,
            regime="backwardation",
            vanna_exposure=-70000.0,
            charm_exposure=12000.0,
            summary="Backwardation with steep put skew",
        ),
        "narrative_context": NarrativeContext(
            earnings=[],
            news=[],
            podcasts=[],
            positioning={},
        ),
        "narrative": "AAPL vol is elevated due to earnings momentum.",
        "trade_recs": [],
        "job_id": "job-test",
        "checkpoints_hit": [],
        "user_inputs": {},
    }


@patch("graphs.trader.nodes.trade_rec._call_claude")
async def test_trade_rec_produces_recommendations(mock_claude):
    mock_claude.return_value = MOCK_CLAUDE_RESPONSE

    state = _make_state()
    result = await trade_rec_node(state)

    assert len(result["trade_recs"]) == 1
    rec = result["trade_recs"][0]
    assert rec.strategy == "calendar_spread"
    assert rec.direction == "long_vol"
    assert len(rec.legs) == 2


@patch("graphs.trader.nodes.trade_rec._call_claude")
async def test_trade_rec_prompt_includes_context(mock_claude):
    mock_claude.return_value = MOCK_CLAUDE_RESPONSE

    state = _make_state()
    await trade_rec_node(state)

    prompt = mock_claude.call_args[0][0]
    assert "backwardation" in prompt.lower()
    assert "calendar" in prompt.lower() or "spread" in prompt.lower()
