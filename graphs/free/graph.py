from langgraph.graph import END, StateGraph

from graphs.free.nodes.load_signals import load_signals_node
from graphs.free.nodes.narrate_gemini import narrate_gemini_node
from graphs.free.state import FreeState
from graphs.shared.compute_vol import compute_vol_node


def build_free_graph():
    """Build and compile the free-tier graph: signals -> vol -> narrate."""
    graph = StateGraph(FreeState)

    graph.add_node("load_signals", load_signals_node)
    graph.add_node("compute_vol", compute_vol_node)
    graph.add_node("narrate_gemini", narrate_gemini_node)

    graph.set_entry_point("load_signals")
    graph.add_edge("load_signals", "compute_vol")
    graph.add_edge("compute_vol", "narrate_gemini")
    graph.add_edge("narrate_gemini", END)

    return graph.compile()
