"""Async market data fetching via Yahoo Finance with crumb authentication."""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx
import structlog

logger = structlog.get_logger()

_YAHOO_BASE = "https://query2.finance.yahoo.com"
_CRUMB_URL = "https://query2.finance.yahoo.com/v1/test/getcrumb"
_COOKIE_URL = "https://fc.yahoo.com"

# Module-level crumb cache
_crumb: str | None = None
_cookies: httpx.Cookies | None = None


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
# Auth helpers
# ---------------------------------------------------------------------------


async def _ensure_crumb(client: httpx.AsyncClient) -> str | None:
    """Obtain a Yahoo crumb token via cookie session."""
    global _crumb, _cookies  # noqa: PLW0603

    if _crumb and _cookies:
        return _crumb

    try:
        # Step 1: Get cookies from Yahoo
        cookie_resp = await client.get(_COOKIE_URL, follow_redirects=True)
        _cookies = cookie_resp.cookies

        # Step 2: Get crumb using cookies
        crumb_resp = await client.get(_CRUMB_URL, cookies=_cookies)
        crumb_resp.raise_for_status()
        _crumb = crumb_resp.text.strip()
        logger.info("yahoo.crumb_obtained", crumb_len=len(_crumb))
        return _crumb
    except Exception:
        logger.warning("yahoo.crumb_failed", exc_info=True)
        return None


async def _yahoo_get(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """Make an authenticated Yahoo Finance request with crumb + cookies."""
    crumb = await _ensure_crumb(client)
    cookies = _cookies or httpx.Cookies()

    if crumb:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}crumb={crumb}"

    resp = await client.get(url, cookies=cookies)
    resp.raise_for_status()
    return resp


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------


async def get_quote(client: httpx.AsyncClient, symbol: str) -> QuoteData | None:
    """Fetch the latest quote for *symbol*."""
    try:
        url = f"{_YAHOO_BASE}/v8/finance/quote?symbols={symbol}"
        resp = await _yahoo_get(client, url)
        data = resp.json()
        result = data["quoteResponse"]["result"]
        if not result:
            return None
        price = result[0].get("regularMarketPrice")
        if price is None:
            return None
        return QuoteData(symbol=symbol, price=float(price))
    except Exception:
        logger.warning("get_quote failed", symbol=symbol, exc_info=True)
        return None


async def get_options_chain(client: httpx.AsyncClient, symbol: str) -> OptionsChainData | None:
    """Fetch option contracts for the nearest 7 expirations."""
    try:
        # First call to get expiration dates
        url = f"{_YAHOO_BASE}/v7/finance/options/{symbol}"
        resp = await _yahoo_get(client, url)
        data = resp.json()

        option_chain = data.get("optionChain", {})
        results = option_chain.get("result", [])
        if not results:
            return None

        first = results[0]
        expirations: list[int] = first.get("expirationDates", [])[:7]
        all_contracts: list[OptionContract] = []

        # Parse contracts from each expiration
        for exp in expirations:
            exp_url = f"{_YAHOO_BASE}/v7/finance/options/{symbol}?date={exp}"
            exp_resp = await _yahoo_get(client, exp_url)
            exp_data = exp_resp.json()

            exp_results = exp_data.get("optionChain", {}).get("result", [])
            if not exp_results:
                continue

            options = exp_results[0].get("options", [])
            if not options:
                continue

            for opt_type in ("calls", "puts"):
                ct = "call" if opt_type == "calls" else "put"
                for c in options[0].get(opt_type, []):
                    iv = c.get("impliedVolatility", 0.0)
                    oi = c.get("openInterest", 0)
                    all_contracts.append(
                        OptionContract(
                            strike=float(c.get("strike", 0)),
                            expiry_epoch=int(c.get("expiration", exp)),
                            type=ct,
                            implied_vol=float(iv),
                            open_interest=int(oi),
                        )
                    )

        return OptionsChainData(symbol=symbol, contracts=all_contracts, expirations=expirations)
    except Exception:
        logger.warning("get_options_chain failed", symbol=symbol, exc_info=True)
        return None


async def get_historical_prices(client: httpx.AsyncClient, symbol: str) -> list[float]:
    """Return 1-year daily closing prices."""
    try:
        url = f"{_YAHOO_BASE}/v8/finance/chart/{symbol}?range=1y&interval=1d"
        resp = await _yahoo_get(client, url)
        data = resp.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return []
        closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
        return [float(c) for c in closes if c is not None]
    except Exception:
        logger.warning("get_historical_prices failed", symbol=symbol, exc_info=True)
        return []


async def get_vix_term_structure(
    client: httpx.AsyncClient,
) -> VixTermStructure | None:
    """Fetch VIX and VIX3M to compute term-structure ratio."""
    try:
        url = f"{_YAHOO_BASE}/v8/finance/quote?symbols=%5EVIX,%5EVIX3M"
        resp = await _yahoo_get(client, url)
        data = resp.json()
        results = data.get("quoteResponse", {}).get("result", [])
        if len(results) < 2:
            return None
        vix_price = float(results[0].get("regularMarketPrice", 0))
        vix3m_price = float(results[1].get("regularMarketPrice", 0))
        if vix3m_price == 0:
            return None
        ratio = vix_price / vix3m_price
        return VixTermStructure(vix=vix_price, vix3m=vix3m_price, backwardation_ratio=ratio)
    except Exception:
        logger.warning("get_vix_term_structure failed", exc_info=True)
        return None
