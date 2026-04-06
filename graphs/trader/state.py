from typing import Annotated, Any, TypedDict

from pydantic import BaseModel

from models.common import ScannerSignals


def _merge_lists(left: list, right: list) -> list:
    """Reducer that merges lists."""
    return left + right


class ConfirmedSignals(BaseModel):
    """Validated and enriched scanner signals."""

    is_valid: bool
    iv_percentile: float
    term_structure_regime: str  # "backwardation" | "contango" | "flat"
    dealer_gamma_regime: str  # "short" | "long" | "neutral"
    composite: float
    summary: str


class VolSurfaceAnalysis(BaseModel):
    """Full vol surface analysis output."""

    term_structure: dict[str, float]
    skew: dict[str, float]
    iv_percentile: float
    regime: str
    vanna_exposure: float
    charm_exposure: float
    summary: str


class NarrativeContext(BaseModel):
    """Aggregated narrative context from all sources."""

    earnings: list[dict[str, str]]
    news: list[dict[str, str]]
    podcasts: list[dict[str, str]]
    positioning: dict[str, Any]


class TradeRecommendation(BaseModel):
    """A structured trade recommendation."""

    strategy: str
    direction: str
    legs: list[dict[str, Any]]
    rationale: str
    estimated_greeks: dict[str, float]
    risk_reward: str


class TraderState(TypedDict):
    """Typed state for the trader analysis graph."""

    # Input
    symbol: str
    scanner_signals: ScannerSignals
    auto_run: bool

    # Phase 1: Signal confirmation
    confirmed_signals: ConfirmedSignals | None

    # Phase 2: Vol surface
    vol_analysis: VolSurfaceAnalysis | None

    # Phase 3: Narrative sources
    narrative_context: NarrativeContext | None

    # Phase 4: Synthesis
    narrative: str

    # Phase 5: Trade recommendation
    trade_recs: list[TradeRecommendation]

    # Metadata
    job_id: str
    checkpoints_hit: list[str]
    user_inputs: dict[str, Any]

    # Logs
    logs: Annotated[list[str], _merge_lists]
