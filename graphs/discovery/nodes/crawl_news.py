from datetime import datetime

import httpx
import structlog

from app.config import Settings
from data.models import CrawlError, RawDocument, SourceType
from graphs.discovery.state import DiscoveryState

logger = structlog.get_logger()

NEWS_API_BASE_URL = "https://newsapi.org/v2"


async def crawl_news_node(state: DiscoveryState) -> dict:
    """Fetch news articles from NewsAPI for target tickers."""
    settings = Settings()
    tickers = state.get("target_tickers") or []
    documents: list[RawDocument] = []
    errors: list[CrawlError] = []

    if not settings.news_api_key:
        return {
            "raw_documents": [],
            "crawl_errors": [
                CrawlError(source_type=SourceType.NEWS, error="NEWS_API_KEY not configured"),
            ],
            "completed_sources": [SourceType.NEWS],
            "logs": ["Skipping news crawl — NEWS_API_KEY not set"],
        }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for ticker in tickers:
            try:
                resp = await client.get(
                    f"{NEWS_API_BASE_URL}/everything",
                    params={"q": ticker, "sortBy": "publishedAt", "pageSize": 10},
                    headers={"X-Api-Key": settings.news_api_key},
                )
                resp.raise_for_status()
                data = resp.json()

                for article in data.get("articles", []):
                    content = article.get("content") or ""
                    if not content:
                        continue
                    documents.append(
                        RawDocument(
                            source_type=SourceType.NEWS,
                            ticker=ticker,
                            title=article.get("title", "Untitled"),
                            url=article.get("url", ""),
                            raw_text=content,
                            published_at=datetime.fromisoformat(
                                article["publishedAt"].replace("Z", "+00:00")
                            ),
                        )
                    )

                logger.info("crawl_news.success", ticker=ticker, count=len(documents))

            except Exception as exc:
                logger.error("crawl_news.error", ticker=ticker, error=str(exc))
                errors.append(
                    CrawlError(
                        source_type=SourceType.NEWS,
                        error=str(exc),
                        ticker=ticker,
                    )
                )

    tickers_str = ", ".join(tickers) if tickers else "none"
    logs = [f"Crawling news for {tickers_str}..."]
    if documents:
        logs.append(f"Found {len(documents)} news articles")
    if errors:
        logs.append(f"News crawl failed: {errors[0].error}")

    return {
        "raw_documents": documents,
        "crawl_errors": errors,
        "completed_sources": [SourceType.NEWS],
        "logs": logs,
    }
