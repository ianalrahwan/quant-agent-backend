from unittest.mock import patch

from graphs.trader.nodes.synthesize import synthesize_node
from graphs.trader.state import (
    ConfirmedSignals,
    NarrativeContext,
    TraderState,
    VolSurfaceAnalysis,
)
from models.common import ScannerSignals


def _make_state() -> TraderState:
    return {
        "symbol": "AAPL",
        "scanner_signals": ScannerSignals(
            iv_percentile=0.85, skew_kurtosis=0.6, dealer_gamma=-0.3,
            term_structure=0.9, vanna=0.7, charm=0.4, composite=0.72,
        ),
        "auto_run": False,
        "confirmed_signals": ConfirmedSignals(
            is_valid=True, iv_percentile=0.85,
            term_structure_regime="backwardation",
            dealer_gamma_regime="short", composite=0.72,
            summary="Strong backwardation with short dealer gamma",
        ),
        "vol_analysis": VolSurfaceAnalysis(
            term_structure={"30d": 0.28, "60d": 0.24, "90d": 0.22},
            skew={"25d_put": 0.31, "atm": 0.22, "25d_call": 0.17},
            iv_percentile=0.85, regime="backwardation",
            vanna_exposure=-70000.0, charm_exposure=12000.0,
            summary="AAPL vol surface: backwardation. Steep put skew.",
        ),
        "narrative_context": NarrativeContext(
            earnings=[{"title": "AAPL Q1", "text": "Revenue up 12%"}],
            news=[{"title": "Apple beat", "text": "Beat expectations"}],
            podcasts=[],
            positioning={},
        ),
        "narrative": "",
        "trade_recs": [],
        "job_id": "job-test",
        "checkpoints_hit": [],
        "user_inputs": {},
    }


@patch("graphs.trader.nodes.synthesize._call_claude")
async def test_synthesize_produces_narrative(mock_claude):
    mock_claude.return_value = (
        "AAPL is experiencing elevated near-term vol driven by "
        "earnings momentum and short dealer gamma positioning."
    )

    state = _make_state()
    result = await synthesize_node(state)

    assert len(result["narrative"]) > 0
    assert "AAPL" in result["narrative"]
    mock_claude.assert_awaited_once()


@patch("graphs.trader.nodes.synthesize._call_claude")
async def test_synthesize_includes_vol_context_in_prompt(mock_claude):
    mock_claude.return_value = "Test narrative."

    state = _make_state()
    await synthesize_node(state)

    call_args = mock_claude.call_args[0][0]
    assert "backwardation" in call_args.lower()
    assert "AAPL" in call_args
