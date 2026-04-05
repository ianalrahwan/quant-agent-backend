from abc import ABC, abstractmethod

from data.models import RawDocument, SourceType


class SourceAdapter(ABC):
    """Abstract interface for data source crawlers."""

    source_type: SourceType

    @abstractmethod
    async def fetch(self, tickers: list[str]) -> list[RawDocument]:
        """Fetch documents for the given tickers."""
        ...
