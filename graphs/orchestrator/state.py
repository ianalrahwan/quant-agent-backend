from typing import Annotated, TypedDict

from pydantic import BaseModel

from graphs.trader.state import TradeRecommendation
from models.common import ScannerSignals


def _merge_lists(left: list, right: list) -> list:
    """Reducer that merges lists."""
    return left + right


class FreshnessReport(BaseModel):
    """Result of checking source freshness for a ticker."""

    stale_sources: list[str]
    fresh_sources: list[str]
    all_fresh: bool


class OrchestratorState(TypedDict):
    """Typed state for the orchestrator graph."""

    # Input
    symbol: str
    scanner_signals: ScannerSignals
    auto_run: bool

    # Freshness
    freshness: FreshnessReport | None
    discovery_needed: bool

    # Results (flattened from trader subgraph)
    trader_narrative: str
    trader_trade_recs: list[TradeRecommendation]

    # Metadata
    job_id: str

    # Logs
    logs: Annotated[list[str], _merge_lists]
