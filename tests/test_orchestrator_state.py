import typing

from graphs.orchestrator.state import FreshnessReport, OrchestratorState


def test_freshness_report():
    report = FreshnessReport(
        stale_sources=["earnings", "news"],
        fresh_sources=["podcast", "cftc"],
        all_fresh=False,
    )
    assert report.all_fresh is False
    assert "earnings" in report.stale_sources


def test_freshness_report_all_fresh():
    report = FreshnessReport(
        stale_sources=[],
        fresh_sources=["earnings", "news", "podcast", "cftc"],
        all_fresh=True,
    )
    assert report.all_fresh is True
    assert len(report.stale_sources) == 0


def test_orchestrator_state_shape():
    hints = typing.get_type_hints(OrchestratorState)
    expected = [
        "symbol",
        "scanner_signals",
        "auto_run",
        "freshness",
        "discovery_needed",
        "trader_narrative",
        "trader_trade_recs",
        "job_id",
    ]
    for key in expected:
        assert key in hints, f"Missing key: {key}"
