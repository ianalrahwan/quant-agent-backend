import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_scheduler_runs_zero_llm_graphs_per_iteration():
    """One iteration of analysis_refresh_loop must NOT invoke any orchestrator graph."""
    from app import scheduler

    fake_app = AsyncMock()
    fake_app.state.session_factory = MagicMock()

    # Capture the real sleep so the test's own yields still work.
    real_sleep = asyncio.sleep

    async def instant_sleep(_delay):
        # Yield one tick so the event loop can make progress, but don't actually wait.
        await real_sleep(0)

    with (
        patch("app.scheduler.run_scan", new=AsyncMock(return_value=[])) as mock_scan,
        patch("app.scheduler.upsert_scanner_result", new=AsyncMock()),
        patch("app.scheduler.delete_stale_scanner_results", new=AsyncMock()),
        patch("app.scheduler.delete_stale_analyses", new=AsyncMock()),
    ):
        scheduler.REFRESH_INTERVAL = 0
        asyncio.sleep = instant_sleep  # type: ignore[assignment]
        try:
            task = asyncio.create_task(scheduler.analysis_refresh_loop(fake_app))
            # Give the event loop enough turns to run past startup sleep and one loop body.
            for _ in range(20):
                await real_sleep(0)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        finally:
            asyncio.sleep = real_sleep  # type: ignore[assignment]

        assert mock_scan.await_count >= 1
        assert not hasattr(scheduler, "build_orchestrator_graph"), (
            "scheduler.py must not import build_orchestrator_graph; scheduler is scanner-only now"
        )
