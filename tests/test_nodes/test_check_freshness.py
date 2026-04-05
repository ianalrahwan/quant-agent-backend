from graphs.orchestrator.nodes.check_freshness import check_freshness_node
from graphs.orchestrator.state import OrchestratorState
from models.common import ScannerSignals


def _make_state(symbol: str = "AAPL") -> OrchestratorState:
    return {
        "symbol": symbol,
        "scanner_signals": ScannerSignals(
            iv_percentile=0.85, skew_kurtosis=0.6, dealer_gamma=-0.3,
            term_structure=0.9, vanna=0.7, charm=0.4, composite=0.72,
        ),
        "auto_run": True,
        "freshness": None,
        "discovery_needed": False,
        "trader_narrative": "",
        "trader_trade_recs": [],
        "job_id": "job-test",
    }


async def test_check_freshness_no_db_marks_stale():
    state = _make_state()
    result = await check_freshness_node(state)
    assert result["freshness"] is not None
    assert result["freshness"].all_fresh is False
    assert result["discovery_needed"] is True
    assert len(result["freshness"].stale_sources) == 4


async def test_check_freshness_returns_source_list():
    state = _make_state()
    result = await check_freshness_node(state)
    report = result["freshness"]
    for source in ["earnings", "news", "podcast", "cftc"]:
        assert source in report.stale_sources or source in report.fresh_sources
