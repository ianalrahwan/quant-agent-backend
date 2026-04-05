from graphs.trader.nodes.signal_confirm import signal_confirm_node
from graphs.trader.state import TraderState
from models.common import ScannerSignals


async def test_signal_confirm_valid():
    state: TraderState = {
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
    result = await signal_confirm_node(state)
    assert result["confirmed_signals"].is_valid is True
    assert result["confirmed_signals"].iv_percentile == 0.85
    assert result["confirmed_signals"].composite == 0.72


async def test_signal_confirm_detects_backwardation():
    state: TraderState = {
        "symbol": "AAPL",
        "scanner_signals": ScannerSignals(
            iv_percentile=0.5,
            skew_kurtosis=0.5,
            dealer_gamma=-0.3,
            term_structure=0.8,
            vanna=0.5,
            charm=0.5,
            composite=0.5,
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
    result = await signal_confirm_node(state)
    signals = result["confirmed_signals"]
    assert signals.term_structure_regime == "backwardation"
    assert signals.dealer_gamma_regime == "short"


async def test_signal_confirm_low_composite_invalid():
    state: TraderState = {
        "symbol": "AAPL",
        "scanner_signals": ScannerSignals(
            iv_percentile=0.1,
            skew_kurtosis=0.1,
            dealer_gamma=0.1,
            term_structure=0.1,
            vanna=0.1,
            charm=0.1,
            composite=0.15,
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
    result = await signal_confirm_node(state)
    assert result["confirmed_signals"].is_valid is False
