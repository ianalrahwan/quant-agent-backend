from datetime import datetime

import httpx
import structlog

from data.models import CrawlError, RawDocument, SourceType
from graphs.discovery.state import DiscoveryState

logger = structlog.get_logger()

FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"


async def crawl_earnings_node(state: DiscoveryState) -> dict:
    """Fetch earnings call transcripts from Financial Modeling Prep API."""
    tickers = state.get("target_tickers") or []
    documents: list[RawDocument] = []
    errors: list[CrawlError] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for ticker in tickers:
            try:
                resp = await client.get(
                    f"{FMP_BASE_URL}/earning_call_transcript/{ticker}"
                )
                resp.raise_for_status()
                transcripts = resp.json()

                for t in transcripts:
                    documents.append(
                        RawDocument(
                            source_type=SourceType.EARNINGS,
                            ticker=ticker,
                            title=f"{ticker} Q{t.get('quarter', '?')} {t.get('year', '?')} Earnings Call",
                            url=f"{FMP_BASE_URL}/earning_call_transcript/{ticker}",
                            raw_text=t.get("content", ""),
                            published_at=datetime.fromisoformat(t["date"]),
                        )
                    )

                logger.info("crawl_earnings.success", ticker=ticker, count=len(transcripts))

            except Exception as exc:
                logger.error("crawl_earnings.error", ticker=ticker, error=str(exc))
                errors.append(
                    CrawlError(
                        source_type=SourceType.EARNINGS,
                        error=str(exc),
                        ticker=ticker,
                    )
                )

    return {
        "raw_documents": documents,
        "crawl_errors": errors,
        "completed_sources": [SourceType.EARNINGS],
    }
