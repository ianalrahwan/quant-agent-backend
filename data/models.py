from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class SourceType(StrEnum):
    EARNINGS = "earnings"
    NEWS = "news"
    PODCAST = "podcast"
    CFTC = "cftc"


class RawDocument(BaseModel):
    """A document fetched by a crawler node."""

    source_type: SourceType
    ticker: str
    title: str
    url: str
    raw_text: str
    published_at: datetime


class CrawlError(BaseModel):
    """An error from a crawler node."""

    source_type: SourceType
    error: str
    ticker: str | None = None


class DocumentChunk(BaseModel):
    """A text chunk with its embedding, ready for pgvector storage."""

    document_title: str
    ticker: str
    source_type: SourceType
    chunk_text: str
    chunk_index: int
    embedding: list[float]
