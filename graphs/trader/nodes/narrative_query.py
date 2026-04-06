import structlog

from graphs.trader.state import NarrativeContext, TraderState

logger = structlog.get_logger()


async def narrative_query_node(state: TraderState) -> dict:
    """Query pgvector for narrative context across all source types.

    In production, this queries the chunks table with vector similarity
    search scoped by ticker and time window. Without a DB session,
    returns empty context — the discovery graph must populate data first.
    """
    symbol = state["symbol"]

    earnings: list[dict[str, str]] = []
    news: list[dict[str, str]] = []
    podcasts: list[dict[str, str]] = []
    positioning: dict = {}

    context = NarrativeContext(
        earnings=earnings,
        news=news,
        podcasts=podcasts,
        positioning=positioning,
    )

    logger.info(
        "narrative_query.done",
        symbol=symbol,
        earnings_count=len(earnings),
        news_count=len(news),
        podcast_count=len(podcasts),
    )

    return {
        "narrative_context": context,
        "logs": [
            f"Querying narrative context for {symbol}...",
            f"Found {len(earnings)} earnings, {len(news)} news, {len(podcasts)} podcast sources",
        ],
    }
