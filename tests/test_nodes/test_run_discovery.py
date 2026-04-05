import respx
from httpx import Response

from graphs.orchestrator.nodes.run_discovery import run_discovery_node
from graphs.orchestrator.state import FreshnessReport, OrchestratorState
from models.common import ScannerSignals


@respx.mock
async def test_run_discovery_invokes_graph():
    respx.get("https://financialmodelingprep.com/api/v3/earning_call_transcript/AAPL").mock(
        return_value=Response(200, json=[])
    )
    respx.route().mock(return_value=Response(200, text=""))

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
        "freshness": FreshnessReport(
            stale_sources=["earnings"],
            fresh_sources=["news", "podcast", "cftc"],
            all_fresh=False,
        ),
        "discovery_needed": True,
        "trader_narrative": "",
        "trader_trade_recs": [],
        "job_id": "job-test",
    }

    result = await run_discovery_node(state)
    assert "discovery_needed" in result
    assert result["discovery_needed"] is False
