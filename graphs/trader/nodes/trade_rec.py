import json

import anthropic
import structlog

from graphs.trader.state import TradeRecommendation, TraderState

logger = structlog.get_logger()


async def _call_claude(prompt: str) -> str:
    """Call Claude API for trade recommendations. Separated for testability."""
    client = anthropic.AsyncAnthropic()
    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _build_prompt(state: TraderState) -> str:
    """Build the trade recommendation prompt."""
    symbol = state["symbol"]
    vol = state.get("vol_analysis")
    signals = state.get("confirmed_signals")
    narrative = state.get("narrative", "")

    parts = [
        f"You are an options strategist. Based on the analysis of {symbol}, "
        f"recommend 1-3 trade structures.\n",
        f"Narrative: {narrative}\n",
    ]

    if vol:
        parts.append(f"Vol regime: {vol.regime}")
        parts.append(f"Term structure: {vol.term_structure}")
        parts.append(f"Skew: {vol.skew}")
        parts.append(f"Vanna exposure: {vol.vanna_exposure:,.0f}\n")

    if signals:
        parts.append(f"Signals: {signals.summary}\n")

    parts.append(
        "Focus on:\n"
        "1. Calendar spreads where backwardation is steepest\n"
        "2. Long-dated vol plays where vanna amplifies directional moves\n"
        "3. Structures suited for an impending bull market\n\n"
        "Return ONLY a JSON array of objects with these fields:\n"
        "strategy, direction, legs (array of {action, expiry, strike, type}), "
        "rationale, estimated_greeks ({delta, vega, theta}), risk_reward"
    )

    return "\n".join(parts)


async def trade_rec_node(state: TraderState) -> dict:
    """Generate trade recommendations using Claude."""
    prompt = _build_prompt(state)

    logger.info("trade_rec.calling_claude", symbol=state["symbol"])
    response = await _call_claude(prompt)

    try:
        recs_data = json.loads(response)
        trade_recs = [TradeRecommendation(**r) for r in recs_data]
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("trade_rec.parse_error", error=str(exc))
        trade_recs = []

    logger.info("trade_rec.done", symbol=state["symbol"], count=len(trade_recs))

    return {
        "trade_recs": trade_recs,
        "logs": [
            f"Generating trade recommendations for {state['symbol']}...",
            f"Generated {len(trade_recs)} trade recommendations",
        ],
    }
