"""Scanner engine — orchestrates data fetching, scoring, and ranking."""

from __future__ import annotations

import asyncio

import httpx
import structlog

from app.scanner.criteria import (
    WEIGHTS,
    score_charm,
    score_dealer_gamma,
    score_iv_percentile,
    score_skew_kurtosis,
    score_term_structure,
    score_vanna,
)
from app.scanner.market_data import (
    get_historical_prices,
    get_options_chain,
    get_quote,
    get_vix_term_structure,
)
from app.scanner.universe import INDEX_SYMBOLS, SCANNER_UNIVERSE
from models.common import ScannerSignals

logger = structlog.get_logger()

COMPOSITE_THRESHOLD = 0.4


async def _score_symbol(
    client: httpx.AsyncClient,
    symbol: str,
    vix: object,
) -> tuple[str, ScannerSignals] | None:
    """Fetch data and compute all 6 scores for a single symbol."""
    quote, chain, prices = await asyncio.gather(
        get_quote(client, symbol),
        get_options_chain(client, symbol),
        get_historical_prices(client, symbol),
    )
    if quote is None or chain is None:
        return None

    spot = quote.price
    is_index = symbol in INDEX_SYMBOLS

    iv_pct = score_iv_percentile(chain, prices, spot)
    skew_k = score_skew_kurtosis(chain, prices, spot)
    d_gamma = score_dealer_gamma(chain, spot)
    term = score_term_structure(chain, spot, vix, is_index)
    van = score_vanna(chain, spot)
    chm = score_charm(chain, spot)

    composite = (
        WEIGHTS["iv_percentile"] * iv_pct
        + WEIGHTS["skew_kurtosis"] * skew_k
        + WEIGHTS["dealer_gamma"] * d_gamma
        + WEIGHTS["term_structure"] * term
        + WEIGHTS["vanna"] * van
        + WEIGHTS["charm"] * chm
    )

    signals = ScannerSignals(
        iv_percentile=round(iv_pct, 4),
        skew_kurtosis=round(skew_k, 4),
        dealer_gamma=round(d_gamma, 4),
        term_structure=round(term, 4),
        vanna=round(van, 4),
        charm=round(chm, 4),
        composite=round(composite, 4),
    )
    return (symbol, signals)


async def run_scan() -> list[tuple[str, ScannerSignals]]:
    """Run the full scanner across the universe and return ranked results."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Fetch VIX term structure once
        vix = await get_vix_term_structure(client)

        # 2. Score symbols with throttling to avoid Yahoo rate limits
        sem = asyncio.Semaphore(3)  # max 3 symbols concurrently

        async def _throttled(sym: str):
            async with sem:
                result = await _score_symbol(client, sym, vix)
                await asyncio.sleep(0.5)  # 500ms delay between completions
                return result

        tasks = [_throttled(sym) for sym in SCANNER_UNIVERSE]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    scored: list[tuple[str, ScannerSignals]] = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning("scanner symbol error", exc_info=r)
            continue
        if r is not None and r[1].composite >= COMPOSITE_THRESHOLD:
            scored.append(r)

    # 3. Sort descending by composite
    scored.sort(key=lambda x: x[1].composite, reverse=True)
    return scored
