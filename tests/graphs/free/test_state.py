def test_free_state_accepts_required_fields():
    from graphs.free.state import FreeState
    from models.common import ScannerSignals

    signals = ScannerSignals(
        iv_percentile=0.5,
        skew_kurtosis=0.5,
        dealer_gamma=0.5,
        term_structure=0.5,
        vanna=0.5,
        charm=0.5,
        composite=0.5,
    )
    state: FreeState = {
        "symbol": "AAPL",
        "scanner_signals": signals,
        "vol_analysis": None,
        "narrative": "",
        "logs": [],
        "job_id": "job-test",
    }
    assert state["symbol"] == "AAPL"
    assert state["scanner_signals"].composite == 0.5
