from datetime import datetime

from data.models import RawDocument, CrawlError, DocumentChunk, SourceType


def test_source_type_values():
    assert SourceType.EARNINGS == "earnings"
    assert SourceType.NEWS == "news"
    assert SourceType.PODCAST == "podcast"
    assert SourceType.CFTC == "cftc"


def test_raw_document():
    doc = RawDocument(
        source_type=SourceType.EARNINGS,
        ticker="AAPL",
        title="AAPL Q1 2026 Earnings Call",
        url="https://example.com/aapl",
        raw_text="Revenue grew 12%...",
        published_at=datetime(2026, 4, 1),
    )
    assert doc.source_type == SourceType.EARNINGS
    assert doc.ticker == "AAPL"


def test_crawl_error():
    err = CrawlError(
        source_type=SourceType.NEWS,
        error="API rate limited",
        ticker="TSLA",
    )
    assert err.source_type == SourceType.NEWS
    assert "rate limited" in err.error


def test_document_chunk():
    chunk = DocumentChunk(
        document_title="AAPL Q1 Earnings",
        ticker="AAPL",
        source_type=SourceType.EARNINGS,
        chunk_text="Revenue grew 12% year over year",
        chunk_index=0,
        embedding=[0.1] * 1024,
    )
    assert chunk.chunk_index == 0
    assert len(chunk.embedding) == 1024
