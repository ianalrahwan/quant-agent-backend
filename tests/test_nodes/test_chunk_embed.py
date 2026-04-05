from datetime import datetime

import respx
from httpx import Response

from data.models import DocumentChunk, RawDocument, SourceType
from graphs.discovery.nodes.chunk_embed import chunk_embed_node, chunk_text
from graphs.discovery.state import DiscoveryState


def test_chunk_text_splits_into_chunks():
    text = "word " * 1000  # ~5000 chars
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 600


def test_chunk_text_short_text_single_chunk():
    text = "Short text."
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) == 1
    assert chunks[0] == "Short text."


@respx.mock
async def test_chunk_embed_node_creates_chunks():
    respx.post("https://api.voyageai.com/v1/embeddings").mock(
        return_value=Response(
            200,
            json={
                "data": [{"embedding": [0.1] * 1024}],
                "usage": {"total_tokens": 100},
            },
        )
    )

    state: DiscoveryState = {
        "trigger_type": "manual",
        "target_tickers": ["AAPL"],
        "source_types": None,
        "raw_documents": [
            RawDocument(
                source_type=SourceType.EARNINGS,
                ticker="AAPL",
                title="AAPL Q1 Earnings",
                url="https://example.com",
                raw_text="Revenue grew 12% year over year. " * 50,
                published_at=datetime(2026, 4, 1),
            )
        ],
        "crawl_errors": [],
        "chunks": [],
        "embeddings_stored": 0,
        "run_id": "test-run",
        "started_at": "2026-04-05T00:00:00",
        "completed_sources": [SourceType.EARNINGS],
    }

    result = await chunk_embed_node(state)

    assert len(result["chunks"]) > 0
    chunk = result["chunks"][0]
    assert isinstance(chunk, DocumentChunk)
    assert chunk.ticker == "AAPL"
    assert chunk.source_type == SourceType.EARNINGS
    assert len(chunk.embedding) == 1024
