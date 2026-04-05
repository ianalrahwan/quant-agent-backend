import pytest

from data.models import RawDocument, SourceType
from data.sources import SourceAdapter


class FakeAdapter(SourceAdapter):
    source_type = SourceType.EARNINGS

    async def fetch(self, tickers: list[str]) -> list[RawDocument]:
        return [
            RawDocument(
                source_type=self.source_type,
                ticker=t,
                title=f"{t} earnings",
                url=f"https://example.com/{t}",
                raw_text="test content",
                published_at="2026-04-01T00:00:00",
            )
            for t in tickers
        ]


async def test_source_adapter_contract():
    adapter = FakeAdapter()
    assert adapter.source_type == SourceType.EARNINGS
    docs = await adapter.fetch(["AAPL"])
    assert len(docs) == 1
    assert docs[0].ticker == "AAPL"


async def test_source_adapter_is_abstract():
    with pytest.raises(TypeError):
        SourceAdapter()  # type: ignore[abstract]
