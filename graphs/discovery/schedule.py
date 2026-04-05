from datetime import datetime, timedelta

from data.models import SourceType

CRAWL_CADENCE: dict[SourceType, timedelta] = {
    SourceType.EARNINGS: timedelta(hours=24),
    SourceType.NEWS: timedelta(hours=1),
    SourceType.PODCAST: timedelta(hours=6),
    SourceType.CFTC: timedelta(days=7),
}


def is_stale(source_type: SourceType, last_run: datetime | None) -> bool:
    """Check if a source is stale and needs recrawling."""
    if last_run is None:
        return True
    cadence = CRAWL_CADENCE.get(source_type, timedelta(hours=24))
    return datetime.utcnow() - last_run > cadence
