from unittest.mock import AsyncMock

from data.models import DocumentChunk, SourceType
from graphs.discovery.nodes.index import index_node, store_chunks


async def test_store_chunks_creates_db_records():
    mock_session = AsyncMock()
    chunks = [
        DocumentChunk(
            document_title="AAPL Q1 Earnings",
            ticker="AAPL",
            source_type=SourceType.EARNINGS,
            chunk_text="Revenue grew 12%",
            chunk_index=0,
            embedding=[0.1] * 1024,
        ),
        DocumentChunk(
            document_title="AAPL Q1 Earnings",
            ticker="AAPL",
            source_type=SourceType.EARNINGS,
            chunk_text="Operating margin improved",
            chunk_index=1,
            embedding=[0.2] * 1024,
        ),
    ]

    count = await store_chunks(mock_session, chunks, "test-run")

    assert count == 2
    assert mock_session.add.call_count > 0
    mock_session.commit.assert_awaited()


async def test_index_node_returns_embeddings_stored():
    chunks = [
        DocumentChunk(
            document_title="Test",
            ticker="AAPL",
            source_type=SourceType.EARNINGS,
            chunk_text="test",
            chunk_index=0,
            embedding=[0.1] * 1024,
        ),
    ]

    state = {
        "trigger_type": "manual",
        "target_tickers": ["AAPL"],
        "source_types": None,
        "raw_documents": [],
        "crawl_errors": [],
        "chunks": chunks,
        "embeddings_stored": 1,
        "run_id": "test-run",
        "started_at": "2026-04-05T00:00:00",
        "completed_sources": [SourceType.EARNINGS],
    }

    result = await index_node(state)
    assert "embeddings_stored" in result
