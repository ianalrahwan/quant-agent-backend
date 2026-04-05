from graphs.trader.nodes.vol_surface import vol_surface_node
from graphs.trader.state import TraderState
from models.common import ScannerSignals


def _make_state(symbol: str = "AAPL") -> TraderState:
    return {
        "symbol": symbol,
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
        "confirmed_signals": None,
        "vol_analysis": None,
        "narrative_context": None,
        "narrative": "",
        "trade_recs": [],
        "job_id": "job-test",
        "checkpoints_hit": [],
        "user_inputs": {},
    }


async def test_vol_surface_produces_analysis():
    state = _make_state()
    result = await vol_surface_node(state)

    analysis = result["vol_analysis"]
    assert analysis is not None
    assert analysis.regime in ("backwardation", "contango", "flat")
    assert isinstance(analysis.term_structure, dict)
    assert isinstance(analysis.skew, dict)
    assert isinstance(analysis.summary, str)
    assert len(analysis.summary) > 0
