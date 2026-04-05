from langgraph.graph import END, StateGraph

from graphs.orchestrator.nodes.check_freshness import check_freshness_node
from graphs.orchestrator.nodes.run_discovery import run_discovery_node
from graphs.orchestrator.nodes.run_trader import run_trader_node
from graphs.orchestrator.state import OrchestratorState


def _route_after_freshness(state: OrchestratorState) -> str:
    """Route to discovery or straight to trader based on freshness."""
    if state.get("discovery_needed", False):
        return "run_discovery"
    return "run_trader"


def build_orchestrator_graph():
    """Build and compile the orchestrator graph."""
    graph = StateGraph(OrchestratorState)

    graph.add_node("check_freshness", check_freshness_node)
    graph.add_node("run_discovery", run_discovery_node)
    graph.add_node("run_trader", run_trader_node)

    graph.set_entry_point("check_freshness")

    graph.add_conditional_edges("check_freshness", _route_after_freshness)

    graph.add_edge("run_discovery", "run_trader")
    graph.add_edge("run_trader", END)

    return graph.compile()
