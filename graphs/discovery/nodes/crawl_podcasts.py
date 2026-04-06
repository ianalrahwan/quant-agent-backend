import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import httpx
import structlog

from data.models import CrawlError, RawDocument, SourceType
from graphs.discovery.state import DiscoveryState

logger = structlog.get_logger()

PODCAST_FEEDS: dict[str, str] = {
    "macro_voices": "https://www.macrovoices.com/podcast-xml",
    "odd_lots": "https://feeds.megaphone.fm/GLT1412515089",
}


async def crawl_podcasts_node(state: DiscoveryState) -> dict:
    """Fetch podcast episodes from RSS feeds and extract descriptions.

    Note: Full Whisper transcription would be added as an enhancement.
    For now, uses episode descriptions as the text content.
    """
    documents: list[RawDocument] = []
    errors: list[CrawlError] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for feed_name, feed_url in PODCAST_FEEDS.items():
            try:
                resp = await client.get(feed_url)
                resp.raise_for_status()

                root = ET.fromstring(resp.text)
                channel = root.find("channel")
                if channel is None:
                    continue

                for item in channel.findall("item"):
                    title = item.findtext("title", "Untitled Episode")
                    link = item.findtext("link", "")
                    pub_date_str = item.findtext("pubDate", "")
                    description = item.findtext("description", "")

                    if not description:
                        continue

                    try:
                        published_at = parsedate_to_datetime(pub_date_str)
                    except (ValueError, TypeError):
                        published_at = datetime.now()

                    documents.append(
                        RawDocument(
                            source_type=SourceType.PODCAST,
                            ticker="MACRO",
                            title=f"[{feed_name}] {title}",
                            url=link,
                            raw_text=description,
                            published_at=published_at,
                        )
                    )

                logger.info("crawl_podcasts.success", feed=feed_name)

            except Exception as exc:
                logger.error("crawl_podcasts.error", feed=feed_name, error=str(exc))
                errors.append(
                    CrawlError(
                        source_type=SourceType.PODCAST,
                        error=f"{feed_name}: {exc}",
                    )
                )

    logs = ["Crawling podcast feeds..."]
    if documents:
        logs.append(f"Found {len(documents)} podcast episodes")
    if errors:
        logs.append(f"Podcast crawl had {len(errors)} feed errors")

    return {
        "raw_documents": documents,
        "crawl_errors": errors,
        "completed_sources": [SourceType.PODCAST],
        "logs": logs,
    }
