from typing import TypedDict

from graphs.trader.state import VolSurfaceAnalysis
from models.common import ScannerSignals


class FreeState(TypedDict, total=False):
    symbol: str
    scanner_signals: ScannerSignals
    vol_analysis: VolSurfaceAnalysis | None
    narrative: str
    logs: list[str]
    job_id: str
