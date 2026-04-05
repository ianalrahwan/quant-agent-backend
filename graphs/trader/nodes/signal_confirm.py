import structlog

from graphs.trader.state import ConfirmedSignals, TraderState

logger = structlog.get_logger()

COMPOSITE_THRESHOLD = 0.3


async def signal_confirm_node(state: TraderState) -> dict:
    """Validate and enrich scanner signals."""
    signals = state["scanner_signals"]

    if signals.term_structure > 0.6:
        ts_regime = "backwardation"
    elif signals.term_structure < 0.4:
        ts_regime = "contango"
    else:
        ts_regime = "flat"

    if signals.dealer_gamma < -0.1:
        dg_regime = "short"
    elif signals.dealer_gamma > 0.1:
        dg_regime = "long"
    else:
        dg_regime = "neutral"

    is_valid = signals.composite >= COMPOSITE_THRESHOLD

    summary_parts = []
    if ts_regime == "backwardation":
        summary_parts.append("Term structure in backwardation")
    if dg_regime == "short":
        summary_parts.append("dealers short gamma")
    if signals.iv_percentile > 0.7:
        summary_parts.append(f"IV at {signals.iv_percentile:.0%} percentile")

    summary = ". ".join(summary_parts) if summary_parts else "No strong signals"

    confirmed = ConfirmedSignals(
        is_valid=is_valid,
        iv_percentile=signals.iv_percentile,
        term_structure_regime=ts_regime,
        dealer_gamma_regime=dg_regime,
        composite=signals.composite,
        summary=summary,
    )

    logger.info("signal_confirm.done", symbol=state["symbol"], valid=is_valid, regime=ts_regime)

    return {"confirmed_signals": confirmed}
