from langgraph.graph import END, StateGraph

from data.models import SourceType
from graphs.discovery.nodes.chunk_embed import chunk_embed_node
from graphs.discovery.nodes.crawl_cftc import crawl_cftc_node
from graphs.discovery.nodes.crawl_earnings import crawl_earnings_node
from graphs.discovery.nodes.crawl_news import crawl_news_node
from graphs.discovery.nodes.crawl_podcasts import crawl_podcasts_node
from graphs.discovery.nodes.index import index_node
from graphs.discovery.state import DiscoveryState


def _route_crawlers(state: DiscoveryState) -> list[str]:
    """Determine which crawler nodes to fan out to."""
    selected = state.get("source_types")
    all_sources = {
        SourceType.EARNINGS: "crawl_earnings",
        SourceType.NEWS: "crawl_news",
        SourceType.PODCAST: "crawl_podcasts",
        SourceType.CFTC: "crawl_cftc",
    }

    if selected is None:
        return list(all_sources.values())

    return [all_sources[s] for s in selected if s in all_sources]


def build_discovery_graph():
    """Build and compile the discovery LangGraph."""
    graph = StateGraph(DiscoveryState)

    # Add nodes
    graph.add_node("crawl_earnings", crawl_earnings_node)
    graph.add_node("crawl_news", crawl_news_node)
    graph.add_node("crawl_podcasts", crawl_podcasts_node)
    graph.add_node("crawl_cftc", crawl_cftc_node)
    graph.add_node("chunk_embed", chunk_embed_node)
    graph.add_node("index", index_node)

    # Fan-out: conditional routing to crawlers
    graph.set_conditional_entry_point(_route_crawlers)

    # Fan-in: all crawlers converge to chunk_embed
    graph.add_edge("crawl_earnings", "chunk_embed")
    graph.add_edge("crawl_news", "chunk_embed")
    graph.add_edge("crawl_podcasts", "chunk_embed")
    graph.add_edge("crawl_cftc", "chunk_embed")

    # chunk_embed -> index -> END
    graph.add_edge("chunk_embed", "index")
    graph.add_edge("index", END)

    return graph.compile()
