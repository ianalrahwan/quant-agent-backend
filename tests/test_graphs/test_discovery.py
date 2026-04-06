import os

import respx
from httpx import Response

from data.models import SourceType
from graphs.discovery.graph import build_discovery_graph
from graphs.discovery.state import DiscoveryState

os.environ.setdefault("FMP_API_KEY", "test-key")
os.environ.setdefault("NEWS_API_KEY", "test-key")

MOCK_FMP_RESPONSE = [
    {
        "symbol": "AAPL",
        "quarter": 1,
        "year": 2026,
        "date": "2026-01-30",
        "content": "Revenue grew 12% year over year.",
    }
]

MOCK_NEWS_RESPONSE = {
    "status": "ok",
    "totalResults": 1,
    "articles": [
        {
            "title": "Apple Revenue",
            "url": "https://example.com/apple",
            "publishedAt": "2026-04-01T14:00:00Z",
            "content": "Apple reported record revenue.",
        }
    ],
}

MOCK_VOYAGE_RESPONSE = {
    "data": [{"embedding": [0.1] * 1024}],
    "usage": {"total_tokens": 100},
}


@respx.mock
async def test_discovery_graph_full_run():
    """Run the full discovery graph with all sources mocked."""
    respx.get("https://financialmodelingprep.com/api/v3/earning_call_transcript/AAPL").mock(
        return_value=Response(200, json=MOCK_FMP_RESPONSE)
    )
    respx.get("https://newsapi.org/v2/everything").mock(
        return_value=Response(200, json=MOCK_NEWS_RESPONSE)
    )
    respx.get("https://www.macrovoices.com/podcast-xml").mock(
        return_value=Response(500, text="Error")
    )
    respx.get("https://feeds.megaphone.fm/GLT1412515089").mock(
        return_value=Response(500, text="Error")
    )
    respx.get("https://www.cftc.gov/dea/newcot/deafut.txt").mock(
        return_value=Response(500, text="Error")
    )
    respx.post("https://api.voyageai.com/v1/embeddings").mock(
        return_value=Response(200, json=MOCK_VOYAGE_RESPONSE)
    )

    graph = build_discovery_graph()

    initial_state: DiscoveryState = {
        "trigger_type": "manual",
        "target_tickers": ["AAPL"],
        "source_types": None,
        "raw_documents": [],
        "crawl_errors": [],
        "chunks": [],
        "embeddings_stored": 0,
        "run_id": "test-full-run",
        "started_at": "2026-04-05T00:00:00",
        "completed_sources": [],
    }

    result = await graph.ainvoke(initial_state)

    # Should have documents from earnings and news (podcasts and cftc failed)
    assert len(result["raw_documents"]) >= 2
    assert len(result["crawl_errors"]) >= 2  # podcast + cftc errors
    assert len(result["completed_sources"]) == 4  # all sources attempted
    assert len(result["chunks"]) > 0


@respx.mock
async def test_discovery_graph_selective_sources():
    """Run with only earnings source selected."""
    respx.get("https://financialmodelingprep.com/api/v3/earning_call_transcript/TSLA").mock(
        return_value=Response(
            200,
            json=[
                {
                    "symbol": "TSLA",
                    "quarter": 1,
                    "year": 2026,
                    "date": "2026-01-30",
                    "content": "Vehicle deliveries increased.",
                }
            ],
        )
    )
    respx.post("https://api.voyageai.com/v1/embeddings").mock(
        return_value=Response(200, json=MOCK_VOYAGE_RESPONSE)
    )

    graph = build_discovery_graph()

    initial_state: DiscoveryState = {
        "trigger_type": "manual",
        "target_tickers": ["TSLA"],
        "source_types": [SourceType.EARNINGS],
        "raw_documents": [],
        "crawl_errors": [],
        "chunks": [],
        "embeddings_stored": 0,
        "run_id": "test-selective",
        "started_at": "2026-04-05T00:00:00",
        "completed_sources": [],
    }

    result = await graph.ainvoke(initial_state)

    assert len(result["raw_documents"]) == 1
    assert result["raw_documents"][0].ticker == "TSLA"
    # Only earnings should have run
    assert SourceType.EARNINGS in result["completed_sources"]
    assert len(result["completed_sources"]) == 1
