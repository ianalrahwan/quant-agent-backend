"""Pure Black-Scholes Greeks — no I/O, no side effects."""

import math

_SQRT_2PI = math.sqrt(2 * math.pi)
_R = 0.05


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT_2PI


def _d1(s: float, k: float, t: float, sigma: float) -> float:
    return (math.log(s / k) + (_R + 0.5 * sigma**2) * t) / (sigma * math.sqrt(t))


def gamma_bs(s: float, k: float, t: float, sigma: float) -> float:
    """Black-Scholes gamma: d²C/dS²."""
    if t <= 0 or sigma <= 0:
        return 0.0
    d = _d1(s, k, t, sigma)
    return _norm_pdf(d) / (s * sigma * math.sqrt(t))


def vanna_bs(s: float, k: float, t: float, sigma: float) -> float:
    """Black-Scholes vanna: dDelta/dVol."""
    if t <= 0 or sigma <= 0:
        return 0.0
    d = _d1(s, k, t, sigma)
    d2 = d - sigma * math.sqrt(t)
    return -d2 * _norm_pdf(d) / sigma


def charm_bs(s: float, k: float, t: float, sigma: float) -> float:
    """Black-Scholes charm: dDelta/dTime."""
    if t <= 0 or sigma <= 0:
        return 0.0
    sqrt_t = math.sqrt(t)
    d = _d1(s, k, t, sigma)
    d2 = d - sigma * sqrt_t
    return -_norm_pdf(d) * (2 * _R * t - d2 * sigma * sqrt_t) / (2 * t * sigma * sqrt_t)
