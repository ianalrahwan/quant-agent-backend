from unittest.mock import AsyncMock, patch

import pytest

from models.common import ScannerSignals


def _signals() -> ScannerSignals:
    return ScannerSignals(
        iv_percentile=0.5,
        skew_kurtosis=0.5,
        dealer_gamma=0.5,
        term_structure=0.5,
        vanna=0.5,
        charm=0.5,
        composite=0.5,
    )


@pytest.mark.asyncio
async def test_free_graph_runs_three_nodes_in_order():
    from graphs.free.graph import build_free_graph
    from graphs.free.nodes import narrate_gemini

    with patch.object(narrate_gemini, "_call_gemini", new=AsyncMock(return_value="ok")):
        graph = build_free_graph()
        state = {
            "symbol": "AAPL",
            "scanner_signals": _signals(),
            "vol_analysis": None,
            "narrative": "",
            "logs": [],
            "job_id": "job-test",
        }
        nodes_seen: list[str] = []
        final_state = state
        async for chunk in graph.astream(state):
            for node_name, output in chunk.items():
                nodes_seen.append(node_name)
                final_state = {**final_state, **output}

        assert "load_signals" in nodes_seen
        assert "compute_vol" in nodes_seen
        assert "narrate_gemini" in nodes_seen
        # Order: load_signals -> compute_vol -> narrate_gemini
        assert nodes_seen.index("load_signals") < nodes_seen.index("compute_vol")
        assert nodes_seen.index("compute_vol") < nodes_seen.index("narrate_gemini")
        # Final state should have narrative set
        assert final_state.get("narrative") == "ok"
