from datetime import datetime
from typing import Annotated, TypedDict

from data.models import CrawlError, DocumentChunk, RawDocument, SourceType


def _merge_lists(left: list, right: list) -> list:
    """Reducer that merges lists (used for accumulating documents/errors)."""
    return left + right


class DiscoveryState(TypedDict):
    """Typed state for the discovery graph."""

    # Input
    trigger_type: str  # "scheduled" or "manual"
    target_tickers: list[str] | None
    source_types: list[SourceType] | None

    # Crawl results (accumulated via reducer)
    raw_documents: Annotated[list[RawDocument], _merge_lists]
    crawl_errors: Annotated[list[CrawlError], _merge_lists]

    # Processing
    chunks: list[DocumentChunk]
    embeddings_stored: int

    # Metadata
    run_id: str
    started_at: datetime
    completed_sources: Annotated[list[SourceType], _merge_lists]

    # Logs
    logs: Annotated[list[str], _merge_lists]
