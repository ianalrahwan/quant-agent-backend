import anthropic
import structlog

from graphs.trader.state import TraderState

logger = structlog.get_logger()


async def _call_claude(prompt: str) -> str:
    """Call Claude API for synthesis. Separated for testability."""
    client = anthropic.AsyncAnthropic()
    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _build_prompt(state: TraderState) -> str:
    """Build the synthesis prompt from trader state."""
    symbol = state["symbol"]
    vol = state.get("vol_analysis")
    signals = state.get("confirmed_signals")
    ctx = state.get("narrative_context")

    parts = [
        f"You are a quantitative volatility analyst. Explain why {symbol} "
        f"has its current options vol regime.\n",
    ]

    if signals:
        parts.append(f"Signal summary: {signals.summary}")
        parts.append(f"Term structure regime: {signals.term_structure_regime}")
        parts.append(f"Dealer gamma: {signals.dealer_gamma_regime}\n")

    if vol:
        parts.append(f"Vol surface: {vol.summary}")
        parts.append(f"IV percentile: {vol.iv_percentile:.0%}")
        parts.append(f"Vanna exposure: {vol.vanna_exposure:,.0f}")
        parts.append(f"Charm exposure: {vol.charm_exposure:,.0f}\n")

    if ctx:
        if ctx.earnings:
            earnings_text = "; ".join(
                f"{e['title']}: {e['text']}" for e in ctx.earnings[:3]
            )
            parts.append(f"Recent earnings: {earnings_text}")
        if ctx.news:
            news_text = "; ".join(
                f"{n['title']}: {n['text']}" for n in ctx.news[:5]
            )
            parts.append(f"Recent news: {news_text}")
        if ctx.podcasts:
            pod_text = "; ".join(
                f"{p['title']}: {p['text']}" for p in ctx.podcasts[:3]
            )
            parts.append(f"Podcast context: {pod_text}")
        if ctx.positioning:
            parts.append(f"Positioning data: {ctx.positioning}")

    parts.append(
        "\nProvide a concise 2-3 paragraph explanation of why this "
        "ticker has this vol regime and what it means for options traders."
    )

    return "\n".join(parts)


async def synthesize_node(state: TraderState) -> dict:
    """Synthesize a narrative explanation using Claude."""
    prompt = _build_prompt(state)

    logger.info("synthesize.calling_claude", symbol=state["symbol"])
    narrative = await _call_claude(prompt)
    logger.info("synthesize.done", symbol=state["symbol"], length=len(narrative))

    return {"narrative": narrative}
