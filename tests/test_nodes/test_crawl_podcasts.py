import respx
from httpx import Response

from data.models import SourceType
from graphs.discovery.nodes.crawl_podcasts import PODCAST_FEEDS, crawl_podcasts_node
from graphs.discovery.state import DiscoveryState

MOCK_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Macro Voices</title>
    <item>
      <title>Episode 420: Volatility Regime Change</title>
      <link>https://podcast.example.com/ep420</link>
      <pubDate>Tue, 01 Apr 2026 12:00:00 GMT</pubDate>
      <description>Discussion of the current vol regime shift.</description>
    </item>
  </channel>
</rss>"""


@respx.mock
async def test_crawl_podcasts_parses_rss():
    for feed_url in PODCAST_FEEDS.values():
        respx.get(feed_url).mock(return_value=Response(200, text=MOCK_RSS))

    state: DiscoveryState = {
        "trigger_type": "manual",
        "target_tickers": None,
        "source_types": [SourceType.PODCAST],
        "raw_documents": [],
        "crawl_errors": [],
        "chunks": [],
        "embeddings_stored": 0,
        "run_id": "test-run",
        "started_at": "2026-04-05T00:00:00",
        "completed_sources": [],
    }

    result = await crawl_podcasts_node(state)

    assert len(result["raw_documents"]) > 0
    doc = result["raw_documents"][0]
    assert doc.source_type == SourceType.PODCAST
    assert "Volatility Regime Change" in doc.title
    assert SourceType.PODCAST in result["completed_sources"]


@respx.mock
async def test_crawl_podcasts_handles_feed_error():
    for feed_url in PODCAST_FEEDS.values():
        respx.get(feed_url).mock(return_value=Response(500, text="Server Error"))

    state: DiscoveryState = {
        "trigger_type": "manual",
        "target_tickers": None,
        "source_types": [SourceType.PODCAST],
        "raw_documents": [],
        "crawl_errors": [],
        "chunks": [],
        "embeddings_stored": 0,
        "run_id": "test-run",
        "started_at": "2026-04-05T00:00:00",
        "completed_sources": [],
    }

    result = await crawl_podcasts_node(state)

    assert len(result["raw_documents"]) == 0
    assert len(result["crawl_errors"]) > 0
    assert SourceType.PODCAST in result["completed_sources"]
