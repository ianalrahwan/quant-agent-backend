import csv
import io
from datetime import datetime

import httpx
import structlog

from data.models import CrawlError, RawDocument, SourceType
from graphs.discovery.state import DiscoveryState

logger = structlog.get_logger()

CFTC_URL = "https://www.cftc.gov/dea/newcot/deafut.txt"


async def crawl_cftc_node(state: DiscoveryState) -> dict:
    """Fetch CFTC Commitments of Traders data and parse positioning."""
    documents: list[RawDocument] = []
    errors: list[CrawlError] = []

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(CFTC_URL)
            resp.raise_for_status()

            reader = csv.DictReader(io.StringIO(resp.text))
            for row in reader:
                market = row.get("Market_and_Exchange_Names", "").strip()
                report_date = row.get("Report_Date_as_YYYY-MM-DD", "")
                long_pos = row.get("NonComm_Positions_Long_All", "0")
                short_pos = row.get("NonComm_Positions_Short_All", "0")

                if not market or not report_date:
                    continue

                net_position = int(long_pos) - int(short_pos)
                positioning_text = (
                    f"Market: {market}\n"
                    f"Report Date: {report_date}\n"
                    f"Non-Commercial Long: {long_pos}\n"
                    f"Non-Commercial Short: {short_pos}\n"
                    f"Net Position: {net_position}"
                )

                documents.append(
                    RawDocument(
                        source_type=SourceType.CFTC,
                        ticker=market.split(" - ")[0].strip(),
                        title=f"CFTC COT: {market} ({report_date})",
                        url=CFTC_URL,
                        raw_text=positioning_text,
                        published_at=datetime.fromisoformat(report_date),
                    )
                )

            logger.info("crawl_cftc.success", count=len(documents))

    except Exception as exc:
        logger.error("crawl_cftc.error", error=str(exc))
        errors.append(CrawlError(source_type=SourceType.CFTC, error=str(exc)))

    return {
        "raw_documents": documents,
        "crawl_errors": errors,
        "completed_sources": [SourceType.CFTC],
    }
