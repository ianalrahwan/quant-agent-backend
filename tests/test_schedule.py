from data.models import SourceType
from graphs.discovery.schedule import CRAWL_CADENCE, is_stale


def test_crawl_cadence_defined():
    assert SourceType.EARNINGS in CRAWL_CADENCE
    assert SourceType.NEWS in CRAWL_CADENCE
    assert SourceType.PODCAST in CRAWL_CADENCE
    assert SourceType.CFTC in CRAWL_CADENCE


def test_earnings_stale_after_24h():
    from datetime import datetime, timedelta

    last_run = datetime.utcnow() - timedelta(hours=25)
    assert is_stale(SourceType.EARNINGS, last_run) is True


def test_earnings_fresh_within_24h():
    from datetime import datetime, timedelta

    last_run = datetime.utcnow() - timedelta(hours=12)
    assert is_stale(SourceType.EARNINGS, last_run) is False


def test_news_stale_after_1h():
    from datetime import datetime, timedelta

    last_run = datetime.utcnow() - timedelta(hours=2)
    assert is_stale(SourceType.NEWS, last_run) is True


def test_none_last_run_is_stale():
    assert is_stale(SourceType.EARNINGS, None) is True
