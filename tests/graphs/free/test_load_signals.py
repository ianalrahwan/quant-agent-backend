import pytest

from models.common import ScannerSignals


@pytest.mark.asyncio
async def test_load_signals_emits_symbol_in_log():
    from graphs.free.nodes.load_signals import load_signals_node

    signals = ScannerSignals(
        iv_percentile=0.7,
        skew_kurtosis=0.4,
        dealer_gamma=0.5,
        term_structure=0.5,
        vanna=0.5,
        charm=0.5,
        composite=0.7,
    )
    state = {"symbol": "AAPL", "scanner_signals": signals}
    result = await load_signals_node(state)
    assert "logs" in result
    assert any("AAPL" in m for m in result["logs"])
