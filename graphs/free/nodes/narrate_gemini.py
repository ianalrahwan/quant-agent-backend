import structlog
from google import genai

from app.dependencies import get_settings
from graphs.free.state import FreeState

logger = structlog.get_logger()

_FALLBACK = (
    "Free-tier model temporarily unavailable. Try again in a moment, "
    "or enter the access password to use the pro analysis."
)


async def _call_gemini(prompt: str) -> str:
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)
    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config={"max_output_tokens": 256, "temperature": 0.7},
    )
    return response.text or _FALLBACK


def _build_prompt(state: FreeState) -> str:
    symbol = state["symbol"]
    signals = state["scanner_signals"]  # ScannerSignals Pydantic model
    vol = state.get("vol_analysis")     # VolSurfaceAnalysis | None

    parts = [
        f"You are a quantitative volatility analyst. Briefly explain (2-3 sentences) "
        f"why {symbol} has its current options vol regime.\n",
        f"Composite score: {signals.composite:.2f}",
        f"IV percentile: {signals.iv_percentile:.2f}",
        f"Term structure score: {signals.term_structure:.2f}",
        f"Dealer gamma score: {signals.dealer_gamma:.2f}",
    ]
    if vol is not None:
        parts.append(f"Vol regime: {vol.regime}")
        parts.append(f"Vol surface summary: {vol.summary}")
    return "\n".join(parts)


async def narrate_gemini_node(state: FreeState) -> dict:
    symbol = state["symbol"]
    prompt = _build_prompt(state)
    logger.info("free.narrate.calling_gemini", symbol=symbol)
    try:
        narrative = await _call_gemini(prompt)
    except Exception as exc:
        logger.warning("free.narrate.gemini_failed", symbol=symbol, error=str(exc))
        narrative = _FALLBACK
    return {
        "narrative": narrative,
        "logs": [
            f"Generating free-tier narrative for {symbol} via Gemini Flash",
            f"Narrative generated ({len(narrative)} chars)",
        ],
    }
