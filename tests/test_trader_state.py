from graphs.trader.state import (
    ConfirmedSignals,
    NarrativeContext,
    TradeRecommendation,
    TraderState,
    VolSurfaceAnalysis,
)


def test_confirmed_signals():
    signals = ConfirmedSignals(
        is_valid=True,
        iv_percentile=0.85,
        term_structure_regime="backwardation",
        dealer_gamma_regime="short",
        composite=0.72,
        summary="Strong backwardation with short dealer gamma",
    )
    assert signals.is_valid is True
    assert signals.term_structure_regime == "backwardation"


def test_vol_surface_analysis():
    analysis = VolSurfaceAnalysis(
        term_structure={"30d": 0.25, "60d": 0.22, "90d": 0.20},
        skew={"25d_put": 0.30, "atm": 0.22, "25d_call": 0.18},
        iv_percentile=0.85,
        regime="backwardation",
        vanna_exposure=-50000.0,
        charm_exposure=12000.0,
        summary="Near-term vol elevated vs. far-term. Steep put skew.",
    )
    assert analysis.regime == "backwardation"
    assert analysis.iv_percentile == 0.85


def test_narrative_context():
    ctx = NarrativeContext(
        earnings=[{"title": "AAPL Q1", "text": "Revenue up 12%"}],
        news=[{"title": "Apple beat", "text": "Beat expectations"}],
        podcasts=[{"title": "Macro ep", "text": "Vol regime shift"}],
        positioning={"net_long": 50000, "change": 5000},
    )
    assert len(ctx.earnings) == 1
    assert ctx.positioning["net_long"] == 50000


def test_trade_recommendation():
    rec = TradeRecommendation(
        strategy="calendar_spread",
        direction="long_vol",
        legs=[
            {"action": "buy", "expiry": "2026-06-19", "strike": 200, "type": "put"},
            {"action": "sell", "expiry": "2026-05-16", "strike": 200, "type": "put"},
        ],
        rationale="Backwardation steepest at 30/60d. Vanna flow supports.",
        estimated_greeks={"delta": -0.05, "vega": 8.2, "theta": -0.3},
        risk_reward="Max loss: debit paid. Target: 50% vol expansion.",
    )
    assert rec.strategy == "calendar_spread"
    assert len(rec.legs) == 2


def test_trader_state_shape():
    """Verify TraderState TypedDict has all expected keys."""
    import typing

    hints = typing.get_type_hints(TraderState)
    expected_keys = [
        "symbol",
        "scanner_signals",
        "auto_run",
        "confirmed_signals",
        "vol_analysis",
        "narrative_context",
        "narrative",
        "trade_recs",
        "job_id",
        "checkpoints_hit",
        "user_inputs",
    ]
    for key in expected_keys:
        assert key in hints, f"Missing key: {key}"
