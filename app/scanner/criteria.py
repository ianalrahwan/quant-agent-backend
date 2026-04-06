"""Six scanner scoring criteria — each returns a float in [0, 1]."""

from __future__ import annotations

import math
import time

from app.scanner.greeks import charm_bs, gamma_bs, vanna_bs
from app.scanner.market_data import OptionsChainData, VixTermStructure


# ---------------------------------------------------------------------------
# Weights (exported for engine.py)
# ---------------------------------------------------------------------------

WEIGHTS = {
    "iv_percentile": 0.25,
    "skew_kurtosis": 0.20,
    "dealer_gamma": 0.20,
    "term_structure": 0.15,
    "vanna": 0.10,
    "charm": 0.10,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _days_to_expiry(epoch: int) -> float:
    """Convert an expiration epoch (seconds) to years remaining."""
    diff = epoch - time.time()
    if diff <= 0:
        return 0.0
    return diff / (365.25 * 86400)


def _atm_iv(chain: OptionsChainData, spot: float, expiry: int) -> float | None:
    """Return the ATM implied vol for a given expiry (nearest strike to spot)."""
    best: float | None = None
    best_dist = float("inf")
    for c in chain.contracts:
        if c.expiry_epoch != expiry:
            continue
        dist = abs(c.strike - spot)
        if dist < best_dist:
            best_dist = dist
            best = c.implied_vol
    return best


def _rolling_realized_vol(prices: list[float], window: int = 30) -> list[float]:
    """Annualised rolling realized vol from daily closes."""
    if len(prices) < window + 1:
        return []
    log_returns = [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]
    result: list[float] = []
    for i in range(window - 1, len(log_returns)):
        chunk = log_returns[i - window + 1 : i + 1]
        mean = sum(chunk) / len(chunk)
        var = sum((r - mean) ** 2 for r in chunk) / (len(chunk) - 1)
        result.append(math.sqrt(var * 252))
    return result


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------


def score_iv_percentile(chain: OptionsChainData, prices: list[float], spot: float) -> float:
    """Compare ATM IV to rolling 30-day realized vol. Cheap vol = high score."""
    if not chain.expirations:
        return 0.0
    iv = _atm_iv(chain, spot, chain.expirations[0])
    if iv is None or iv <= 0:
        return 0.0
    rvols = _rolling_realized_vol(prices)
    if not rvols:
        return 0.5
    count_below = sum(1 for rv in rvols if rv < iv)
    pct = count_below / len(rvols)
    # Lower percentile = vol is cheap relative to history = higher score
    return 1.0 - pct


def score_skew_kurtosis(chain: OptionsChainData, prices: list[float], spot: float) -> float:
    """Put skew (95% strike) + excess kurtosis. Mismatch = bonus."""
    # --- put skew ---
    target_strike = spot * 0.95
    if not chain.expirations:
        return 0.0
    exp0 = chain.expirations[0]
    atm = _atm_iv(chain, spot, exp0)

    # Find nearest put to 95% strike
    best_put_iv: float | None = None
    best_dist = float("inf")
    for c in chain.contracts:
        if c.expiry_epoch != exp0 or c.type != "put":
            continue
        d = abs(c.strike - target_strike)
        if d < best_dist:
            best_dist = d
            best_put_iv = c.implied_vol
    skew = 0.0
    if atm and best_put_iv and atm > 0:
        skew = (best_put_iv - atm) / atm  # positive = puts richer

    # --- excess kurtosis from returns ---
    if len(prices) < 31:
        kurt = 0.0
    else:
        log_ret = [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]
        n = len(log_ret)
        mean = sum(log_ret) / n
        var = sum((r - mean) ** 2 for r in log_ret) / n
        if var <= 0:
            kurt = 0.0
        else:
            m4 = sum((r - mean) ** 4 for r in log_ret) / n
            kurt = m4 / var**2 - 3.0  # excess kurtosis

    # Combine: higher skew and higher kurtosis = higher score
    raw = 0.5 * min(max(skew * 5, 0), 1) + 0.5 * min(max(kurt / 5, 0), 1)
    return max(0.0, min(1.0, raw))


def score_dealer_gamma(chain: OptionsChainData, spot: float) -> float:
    """Net GEX (gamma exposure). Negative = short gamma = higher score."""
    total_gex = 0.0
    for c in chain.contracts:
        t = _days_to_expiry(c.expiry_epoch)
        if t <= 0 or c.implied_vol <= 0:
            continue
        g = gamma_bs(spot, c.strike, t, c.implied_vol)
        contract_gex = g * c.open_interest * 100 * spot
        if c.type == "put":
            contract_gex = -contract_gex
        total_gex += contract_gex

    # Normalise: negative GEX → higher score
    n = -total_gex / (abs(total_gex) + 1e8)
    return 0.5 + n * 0.5


def score_term_structure(
    chain: OptionsChainData,
    spot: float,
    vix: VixTermStructure | None,
    is_index: bool,
) -> float:
    """Backwardation = high score."""
    if is_index and vix is not None:
        # VIX / VIX3M — ratio > 1 = backwardation
        ratio = vix.backwardation_ratio
        return max(0.0, min(1.0, ratio - 0.5))  # maps 0.5→0, 1.0→0.5, 1.5→1

    # For stocks: compare near-term IV to far-term IV
    if len(chain.expirations) < 2:
        return 0.5
    near_iv = _atm_iv(chain, spot, chain.expirations[0])
    far_iv = _atm_iv(chain, spot, chain.expirations[-1])
    if near_iv is None or far_iv is None or far_iv <= 0:
        return 0.5
    ratio = near_iv / far_iv
    return max(0.0, min(1.0, ratio - 0.5))


def score_vanna(chain: OptionsChainData, spot: float) -> float:
    """Net vanna. Normalise: -total/(|total|+1e6), then 0.5+n*0.5."""
    total = 0.0
    for c in chain.contracts:
        t = _days_to_expiry(c.expiry_epoch)
        if t <= 0 or c.implied_vol <= 0:
            continue
        v = vanna_bs(spot, c.strike, t, c.implied_vol)
        total += v * c.open_interest * 100

    n = -total / (abs(total) + 1e6)
    return 0.5 + n * 0.5


def score_charm(chain: OptionsChainData, spot: float) -> float:
    """|Net charm|. Normalise: mag/(mag+1e5)."""
    total = 0.0
    for c in chain.contracts:
        t = _days_to_expiry(c.expiry_epoch)
        if t <= 0 or c.implied_vol <= 0:
            continue
        ch = charm_bs(spot, c.strike, t, c.implied_vol)
        total += ch * c.open_interest * 100

    mag = abs(total)
    return mag / (mag + 1e5)
