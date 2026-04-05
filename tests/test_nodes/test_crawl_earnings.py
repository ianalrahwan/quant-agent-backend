import respx
from httpx import Response

from data.models import SourceType
from graphs.discovery.nodes.crawl_earnings import crawl_earnings_node
from graphs.discovery.state import DiscoveryState

FMP_TRANSCRIPT_RESPONSE = [
    {
        "symbol": "AAPL",
        "quarter": 1,
        "year": 2026,
        "date": "2026-01-30",
        "content": "Good afternoon everyone. Revenue grew 12% year over year to $124 billion.",
    }
]


@respx.mock
async def test_crawl_earnings_fetches_transcripts():
    respx.get("https://financialmodelingprep.com/api/v3/earning_call_transcript/AAPL").mock(
        return_value=Response(200, json=FMP_TRANSCRIPT_RESPONSE)
    )

    state: DiscoveryState = {
        "trigger_type": "manual",
        "target_tickers": ["AAPL"],
        "source_types": [SourceType.EARNINGS],
        "raw_documents": [],
        "crawl_errors": [],
        "chunks": [],
        "embeddings_stored": 0,
        "run_id": "test-run",
        "started_at": "2026-04-05T00:00:00",
        "completed_sources": [],
    }

    result = await crawl_earnings_node(state)

    assert len(result["raw_documents"]) == 1
    doc = result["raw_documents"][0]
    assert doc.ticker == "AAPL"
    assert doc.source_type == SourceType.EARNINGS
    assert "Revenue grew 12%" in doc.raw_text
    assert SourceType.EARNINGS in result["completed_sources"]


@respx.mock
async def test_crawl_earnings_handles_api_error():
    respx.get("https://financialmodelingprep.com/api/v3/earning_call_transcript/AAPL").mock(
        return_value=Response(500, text="Internal Server Error")
    )

    state: DiscoveryState = {
        "trigger_type": "manual",
        "target_tickers": ["AAPL"],
        "source_types": [SourceType.EARNINGS],
        "raw_documents": [],
        "crawl_errors": [],
        "chunks": [],
        "embeddings_stored": 0,
        "run_id": "test-run",
        "started_at": "2026-04-05T00:00:00",
        "completed_sources": [],
    }

    result = await crawl_earnings_node(state)

    assert len(result["raw_documents"]) == 0
    assert len(result["crawl_errors"]) == 1
    assert result["crawl_errors"][0].source_type == SourceType.EARNINGS
    assert SourceType.EARNINGS in result["completed_sources"]
