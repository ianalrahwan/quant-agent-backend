import respx
from httpx import Response

from data.models import SourceType
from graphs.discovery.nodes.crawl_cftc import crawl_cftc_node
from graphs.discovery.state import DiscoveryState

MOCK_CFTC_CSV = (
    "Market_and_Exchange_Names,Report_Date_as_YYYY-MM-DD,"
    "NonComm_Positions_Long_All,NonComm_Positions_Short_All\n"
    "CRUDE OIL - NEW YORK MERCANTILE EXCHANGE,2026-04-01,300000,250000\n"
    "GOLD - COMMODITY EXCHANGE INC.,2026-04-01,200000,150000"
)


@respx.mock
async def test_crawl_cftc_parses_csv():
    respx.get("https://www.cftc.gov/dea/newcot/deafut.txt").mock(
        return_value=Response(200, text=MOCK_CFTC_CSV)
    )

    state: DiscoveryState = {
        "trigger_type": "manual",
        "target_tickers": None,
        "source_types": [SourceType.CFTC],
        "raw_documents": [],
        "crawl_errors": [],
        "chunks": [],
        "embeddings_stored": 0,
        "run_id": "test-run",
        "started_at": "2026-04-05T00:00:00",
        "completed_sources": [],
    }

    result = await crawl_cftc_node(state)

    assert len(result["raw_documents"]) > 0
    doc = result["raw_documents"][0]
    assert doc.source_type == SourceType.CFTC
    assert "CRUDE OIL" in doc.title or "GOLD" in doc.title
    assert SourceType.CFTC in result["completed_sources"]


@respx.mock
async def test_crawl_cftc_handles_error():
    respx.get("https://www.cftc.gov/dea/newcot/deafut.txt").mock(
        return_value=Response(503, text="Unavailable")
    )

    state: DiscoveryState = {
        "trigger_type": "manual",
        "target_tickers": None,
        "source_types": [SourceType.CFTC],
        "raw_documents": [],
        "crawl_errors": [],
        "chunks": [],
        "embeddings_stored": 0,
        "run_id": "test-run",
        "started_at": "2026-04-05T00:00:00",
        "completed_sources": [],
    }

    result = await crawl_cftc_node(state)

    assert len(result["raw_documents"]) == 0
    assert len(result["crawl_errors"]) == 1
    assert SourceType.CFTC in result["completed_sources"]
