"""Market data fetching via yfinance (handles Yahoo auth automatically)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from functools import partial

import structlog
import yfinance as yf

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class QuoteData:
    symbol: str
    price: float


@dataclass
class OptionContract:
    strike: float
    expiry_epoch: int
    type: str  # "call" | "put"
    implied_vol: float
    open_interest: int


@dataclass
class OptionsChainData:
    symbol: str
    contracts: list[OptionContract] = field(default_factory=list)
    expirations: list[int] = field(default_factory=list)


@dataclass
class VixTermStructure:
    vix: float
    vix3m: float
    backwardation_ratio: float


# ---------------------------------------------------------------------------
# Sync helpers (yfinance is sync — we run in executor)
# ---------------------------------------------------------------------------


def _get_quote_sync(symbol: str) -> QuoteData | None:
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = getattr(info, "last_price", None)
        if price is None:
            return None
        return QuoteData(symbol=symbol, price=float(price))
    except Exception:
        logger.warning("get_quote failed", symbol=symbol, exc_info=True)
        return None


def _get_options_chain_sync(symbol: str) -> OptionsChainData | None:
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        if not expirations:
            return None

        # Take nearest 7 expirations
        selected = expirations[:7]
        all_contracts: list[OptionContract] = []
        exp_epochs: list[int] = []

        for exp_str in selected:
            chain = ticker.option_chain(exp_str)
            from datetime import datetime

            exp_epoch = int(datetime.strptime(exp_str, "%Y-%m-%d").timestamp())
            exp_epochs.append(exp_epoch)

            for _, row in chain.calls.iterrows():
                iv = row.get("impliedVolatility", 0.0)
                oi = row.get("openInterest", 0)
                all_contracts.append(
                    OptionContract(
                        strike=float(row["strike"]),
                        expiry_epoch=exp_epoch,
                        type="call",
                        implied_vol=float(iv) if iv == iv else 0.0,  # NaN check
                        open_interest=int(oi) if oi == oi else 0,
                    )
                )

            for _, row in chain.puts.iterrows():
                iv = row.get("impliedVolatility", 0.0)
                oi = row.get("openInterest", 0)
                all_contracts.append(
                    OptionContract(
                        strike=float(row["strike"]),
                        expiry_epoch=exp_epoch,
                        type="put",
                        implied_vol=float(iv) if iv == iv else 0.0,
                        open_interest=int(oi) if oi == oi else 0,
                    )
                )

        return OptionsChainData(symbol=symbol, contracts=all_contracts, expirations=exp_epochs)
    except Exception:
        logger.warning("get_options_chain failed", symbol=symbol, exc_info=True)
        return None


def _get_historical_prices_sync(symbol: str) -> list[float]:
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y", interval="1d")
        if hist.empty:
            return []
        return [float(c) for c in hist["Close"].dropna().tolist()]
    except Exception:
        logger.warning("get_historical_prices failed", symbol=symbol, exc_info=True)
        return []


def _get_vix_term_structure_sync() -> VixTermStructure | None:
    try:
        vix_ticker = yf.Ticker("^VIX")
        vix3m_ticker = yf.Ticker("^VIX3M")
        vix_price = getattr(vix_ticker.fast_info, "last_price", None)
        vix3m_price = getattr(vix3m_ticker.fast_info, "last_price", None)
        if vix_price is None or vix3m_price is None or vix3m_price == 0:
            return None
        ratio = float(vix_price) / float(vix3m_price)
        return VixTermStructure(
            vix=float(vix_price), vix3m=float(vix3m_price), backwardation_ratio=ratio
        )
    except Exception:
        logger.warning("get_vix_term_structure failed", exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Async wrappers (run sync yfinance in thread pool)
# ---------------------------------------------------------------------------


async def get_quote(_client, symbol: str) -> QuoteData | None:
    """Fetch the latest quote for *symbol*."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_get_quote_sync, symbol))


async def get_options_chain(_client, symbol: str) -> OptionsChainData | None:
    """Fetch option contracts for the nearest 7 expirations."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_get_options_chain_sync, symbol))


async def get_historical_prices(_client, symbol: str) -> list[float]:
    """Return 1-year daily closing prices."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_get_historical_prices_sync, symbol))


async def get_vix_term_structure(_client=None) -> VixTermStructure | None:
    """Fetch VIX and VIX3M to compute term-structure ratio."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _get_vix_term_structure_sync)
