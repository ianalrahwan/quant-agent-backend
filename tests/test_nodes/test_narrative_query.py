from graphs.trader.nodes.narrative_query import narrative_query_node
from graphs.trader.state import TraderState
from models.common import ScannerSignals


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
        "confirmed_signals": None,
        "vol_analysis": None,
        "narrative_context": None,
        "narrative": "",
        "trade_recs": [],
        "job_id": "job-test",
        "checkpoints_hit": [],
        "user_inputs": {},
    }


async def test_narrative_query_returns_context_shape():
    state = _make_state()
    result = await narrative_query_node(state)

    ctx = result["narrative_context"]
    assert ctx is not None
    assert isinstance(ctx.earnings, list)
    assert isinstance(ctx.news, list)
    assert isinstance(ctx.podcasts, list)
    assert isinstance(ctx.positioning, dict)
