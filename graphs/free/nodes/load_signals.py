import structlog

from graphs.free.state import FreeState

logger = structlog.get_logger()


async def load_signals_node(state: FreeState) -> dict:
    """Pass-through: scanner_signals are already in input state. Log the entry."""
    symbol = state["symbol"]
    logger.info("free.load_signals", symbol=symbol)
    return {
        "logs": [f"Loaded scanner signals for {symbol}"],
    }
