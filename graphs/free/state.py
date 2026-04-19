from typing import Annotated, TypedDict

from graphs.trader.state import VolSurfaceAnalysis, _merge_lists
from models.common import ScannerSignals


class FreeState(TypedDict, total=False):
    symbol: str
    scanner_signals: ScannerSignals
    vol_analysis: VolSurfaceAnalysis | None
    narrative: str
    logs: Annotated[list[str], _merge_lists]
    job_id: str
