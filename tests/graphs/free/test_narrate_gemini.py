from unittest.mock import AsyncMock, patch

import pytest

from models.common import ScannerSignals


def _signals(**overrides) -> ScannerSignals:
    base = dict(
        iv_percentile=0.7,
        skew_kurtosis=0.4,
        dealer_gamma=0.5,
        term_structure=0.5,
        vanna=0.5,
        charm=0.5,
        composite=0.7,
    )
    base.update(overrides)
    return ScannerSignals(**base)


@pytest.mark.asyncio
async def test_narrate_calls_gemini_and_returns_narrative():
    from graphs.free.nodes import narrate_gemini

    return_val = "AAPL is in a stressed vol regime."
    with patch.object(narrate_gemini, "_call_gemini", new=AsyncMock(return_value=return_val)):
        state = {
            "symbol": "AAPL",
            "scanner_signals": _signals(),
            "vol_analysis": None,
        }
        result = await narrate_gemini.narrate_gemini_node(state)
        assert "AAPL" in result["narrative"]
        assert "logs" in result
        assert len(result["logs"]) >= 1


@pytest.mark.asyncio
async def test_narrate_returns_fallback_on_gemini_error():
    from graphs.free.nodes import narrate_gemini

    with patch.object(
        narrate_gemini, "_call_gemini", new=AsyncMock(side_effect=RuntimeError("api down"))
    ):
        state = {"symbol": "AAPL", "scanner_signals": _signals(), "vol_analysis": None}
        result = await narrate_gemini.narrate_gemini_node(state)
        assert (
            "temporarily unavailable" in result["narrative"].lower()
            or "try again" in result["narrative"].lower()
        )


@pytest.mark.asyncio
async def test_prompt_uses_attribute_access_not_dict_access():
    """Regression: scanner_signals is a Pydantic model, not a dict.

    Builder must use attribute access, not dict .get().
    """
    from graphs.free.nodes.narrate_gemini import _build_prompt

    state = {"symbol": "AAPL", "scanner_signals": _signals(composite=0.91), "vol_analysis": None}
    prompt = _build_prompt(state)
    # composite 0.91 should surface in the prompt text
    assert "0.91" in prompt or "91" in prompt
