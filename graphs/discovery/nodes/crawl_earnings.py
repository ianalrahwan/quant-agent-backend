from datetime import datetime

import httpx
import structlog

from app.config import Settings
from data.models import CrawlError, RawDocument, SourceType
from graphs.discovery.state import DiscoveryState

logger = structlog.get_logger()

FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"


async def crawl_earnings_node(state: DiscoveryState) -> dict:
    """Fetch earnings call transcripts from Financial Modeling Prep API."""
    settings = Settings()
    tickers = state.get("target_tickers") or []
    documents: list[RawDocument] = []
    errors: list[CrawlError] = []

    if not settings.fmp_api_key:
        return {
            "raw_documents": [],
            "crawl_errors": [
                CrawlError(source_type=SourceType.EARNINGS, error="FMP_API_KEY not configured"),
            ],
            "completed_sources": [SourceType.EARNINGS],
            "logs": ["Skipping earnings crawl — FMP_API_KEY not set"],
        }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for ticker in tickers:
            try:
                resp = await client.get(
                    f"{FMP_BASE_URL}/earning_call_transcript/{ticker}",
                    params={"apikey": settings.fmp_api_key},
                )
                resp.raise_for_status()
                transcripts = resp.json()

                for t in transcripts:
                    documents.append(
                        RawDocument(
                            source_type=SourceType.EARNINGS,
                            ticker=ticker,
                            title=(
                                f"{ticker} Q{t.get('quarter', '?')}"
                                f" {t.get('year', '?')} Earnings Call"
                            ),
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

    tickers_str = ", ".join(tickers) if tickers else "none"
    logs = [f"Crawling earnings transcripts for {tickers_str}..."]
    if documents:
        logs.append(f"Found {len(documents)} earnings transcripts")
    if errors:
        logs.append(f"Earnings crawl failed: {errors[0].error}")

    return {
        "raw_documents": documents,
        "crawl_errors": errors,
        "completed_sources": [SourceType.EARNINGS],
        "logs": logs,
    }
