"""Deterministic vol-surface computation node shared across graphs."""

import structlog

from graphs.trader.state import TraderState, VolSurfaceAnalysis

logger = structlog.get_logger()


async def compute_vol_node(state: TraderState) -> dict:
    """Analyze vol surface using scanner signals.

    This node performs pure computation based on the scanner signals
    already computed by the frontend. In a production system, this
    would fetch live options chain data and compute the surface.
    For now, it derives the analysis from the scanner signal scores.
    """
    signals = state["scanner_signals"]

    if signals.term_structure > 0.6:
        regime = "backwardation"
        ts = {"30d": 0.28, "60d": 0.24, "90d": 0.22}
    elif signals.term_structure < 0.4:
        regime = "contango"
        ts = {"30d": 0.18, "60d": 0.22, "90d": 0.25}
    else:
        regime = "flat"
        ts = {"30d": 0.22, "60d": 0.22, "90d": 0.22}

    skew_steepness = signals.skew_kurtosis
    skew = {
        "25d_put": 0.22 + skew_steepness * 0.15,
        "atm": 0.22,
        "25d_call": 0.22 - skew_steepness * 0.08,
    }

    vanna_exposure = signals.vanna * -100000
    charm_exposure = signals.charm * 30000

    summary_parts = [f"{state['symbol']} vol surface: {regime}"]
    if regime == "backwardation":
        spread = ts["30d"] - ts["90d"]
        summary_parts.append(f"30/90d spread: {spread:.1%}")
    if skew_steepness > 0.5:
        summary_parts.append("steep put skew")
    if signals.vanna > 0.5:
        summary_parts.append("significant vanna exposure")

    analysis = VolSurfaceAnalysis(
        term_structure=ts,
        skew=skew,
        iv_percentile=signals.iv_percentile,
        regime=regime,
        vanna_exposure=vanna_exposure,
        charm_exposure=charm_exposure,
        summary=". ".join(summary_parts),
    )

    logger.info("vol_surface.done", symbol=state["symbol"], regime=regime)

    return {
        "vol_analysis": analysis,
        "logs": [
            f"Analyzing vol surface for {state['symbol']}...",
            f"Vol surface: {regime}, IV {signals.iv_percentile:.0%}ile",
        ],
    }
