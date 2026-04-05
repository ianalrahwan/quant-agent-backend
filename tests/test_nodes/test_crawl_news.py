import respx
from httpx import Response

from data.models import SourceType
from graphs.discovery.nodes.crawl_news import crawl_news_node
from graphs.discovery.state import DiscoveryState

NEWS_API_RESPONSE = {
    "status": "ok",
    "totalResults": 1,
    "articles": [
        {
            "title": "Apple Reports Record Revenue",
            "url": "https://news.example.com/apple-revenue",
            "publishedAt": "2026-04-01T14:00:00Z",
            "content": "Apple reported record quarterly revenue of $124B.",
        }
    ],
}


@respx.mock
async def test_crawl_news_fetches_articles():
    respx.get("https://newsapi.org/v2/everything").mock(
        return_value=Response(200, json=NEWS_API_RESPONSE)
    )

    state: DiscoveryState = {
        "trigger_type": "manual",
        "target_tickers": ["AAPL"],
        "source_types": [SourceType.NEWS],
        "raw_documents": [],
        "crawl_errors": [],
        "chunks": [],
        "embeddings_stored": 0,
        "run_id": "test-run",
        "started_at": "2026-04-05T00:00:00",
        "completed_sources": [],
    }

    result = await crawl_news_node(state)

    assert len(result["raw_documents"]) == 1
    doc = result["raw_documents"][0]
    assert doc.ticker == "AAPL"
    assert doc.source_type == SourceType.NEWS
    assert "quarterly revenue" in doc.raw_text
    assert SourceType.NEWS in result["completed_sources"]


@respx.mock
async def test_crawl_news_handles_api_error():
    respx.get("https://newsapi.org/v2/everything").mock(
        return_value=Response(429, text="Rate limited")
    )

    state: DiscoveryState = {
        "trigger_type": "manual",
        "target_tickers": ["AAPL"],
        "source_types": [SourceType.NEWS],
        "raw_documents": [],
        "crawl_errors": [],
        "chunks": [],
        "embeddings_stored": 0,
        "run_id": "test-run",
        "started_at": "2026-04-05T00:00:00",
        "completed_sources": [],
    }

    result = await crawl_news_node(state)

    assert len(result["raw_documents"]) == 0
    assert len(result["crawl_errors"]) == 1
    assert SourceType.NEWS in result["completed_sources"]
