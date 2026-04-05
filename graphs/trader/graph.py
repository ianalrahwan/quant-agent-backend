from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from graphs.trader.nodes.narrative_query import narrative_query_node
from graphs.trader.nodes.signal_confirm import signal_confirm_node
from graphs.trader.nodes.synthesize import synthesize_node
from graphs.trader.nodes.trade_rec import trade_rec_node
from graphs.trader.nodes.vol_surface import vol_surface_node
from graphs.trader.state import TraderState


def _should_continue(state: TraderState) -> str:
    """Route after signal_confirm: continue or end."""
    signals = state.get("confirmed_signals")
    if signals and not signals.is_valid:
        return END
    return "vol_surface"


def build_trader_graph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> StateGraph:
    """Build and compile the trader analysis graph.

    With checkpointer=None (auto_run), no interrupts.
    With a checkpointer, interrupts after vol_surface, narrative_query, synthesize.
    """
    graph = StateGraph(TraderState)

    # Add all nodes
    graph.add_node("signal_confirm", signal_confirm_node)
    graph.add_node("vol_surface", vol_surface_node)
    graph.add_node("narrative_query", narrative_query_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("trade_rec", trade_rec_node)

    # Entry -> signal_confirm
    graph.set_entry_point("signal_confirm")

    # signal_confirm -> conditional: continue or end
    graph.add_conditional_edges("signal_confirm", _should_continue)

    # Linear flow with checkpoint interrupts
    graph.add_edge("vol_surface", "narrative_query")
    graph.add_edge("narrative_query", "synthesize")
    graph.add_edge("synthesize", "trade_rec")
    graph.add_edge("trade_rec", END)

    # Compile with optional checkpointer and interrupt points
    interrupt_before = []
    if checkpointer is not None:
        interrupt_before = ["narrative_query", "synthesize", "trade_rec"]

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before if interrupt_before else None,
    )
