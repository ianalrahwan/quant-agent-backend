"""Tests for scanner Greeks and criteria helpers."""

from app.scanner.criteria import _rolling_realized_vol
from app.scanner.greeks import charm_bs, gamma_bs, vanna_bs

# ---------------------------------------------------------------------------
# Rolling realized vol
# ---------------------------------------------------------------------------


def test_rolling_realized_vol_basic():
    """Constant prices → zero realised vol."""
    prices = [100.0] * 50
    result = _rolling_realized_vol(prices, window=30)
    assert len(result) > 0
    assert all(v == 0.0 for v in result)


def test_rolling_realized_vol_too_short():
    """Fewer than window+1 prices → empty list."""
    prices = [100.0] * 20
    result = _rolling_realized_vol(prices, window=30)
    assert result == []


# ---------------------------------------------------------------------------
# Greeks
# ---------------------------------------------------------------------------


def test_gamma_bs_positive():
    """ATM gamma should be positive."""
    g = gamma_bs(s=100, k=100, t=0.25, sigma=0.2)
    assert g > 0


def test_gamma_bs_zero_time():
    """Gamma at t=0 must return 0."""
    g = gamma_bs(s=100, k=100, t=0, sigma=0.2)
    assert g == 0.0


def test_vanna_bs_atm():
    """ATM vanna is non-zero."""
    v = vanna_bs(s=100, k=100, t=0.25, sigma=0.2)
    assert v != 0.0


def test_charm_bs_atm():
    """ATM charm is non-zero."""
    c = charm_bs(s=100, k=100, t=0.25, sigma=0.2)
    assert c != 0.0
