from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.dependencies import override_settings
from app.main import create_app
from sse.bus import InMemorySSEBus


async def _empty_aiter(_state):
    # matches an async iterator protocol
    if False:
        yield  # pragma: no cover


def _make_app():
    a = create_app()
    a.state.sse_bus = InMemorySSEBus()
    a.state.session_factory = None
    rate_limiter = MagicMock()
    rate_limiter.check = AsyncMock(return_value=None)
    a.state.rate_limiter = rate_limiter
    return a


@pytest.fixture
async def client():
    a = _make_app()
    transport = ASGITransport(app=a)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _payload() -> dict:
    return {
        "scanner_signals": {
            "iv_percentile": 0.5,
            "skew_kurtosis": 0.5,
            "dealer_gamma": 0.5,
            "term_structure": 0.5,
            "vanna": 0.5,
            "charm": 0.5,
            "composite": 0.5,
        },
        "auto_run": False,
    }


async def test_post_without_token_routes_to_free_graph(client):
    override_settings(Settings(pro_tier_token="secret"))
    try:
        with (
            patch("app.routes.analysis.build_free_graph") as mock_free,
            patch("app.routes.analysis.build_orchestrator_graph") as mock_pro,
        ):
            mock_free.return_value = MagicMock()
            mock_free.return_value.astream = _empty_aiter
            mock_pro.return_value = MagicMock()
            mock_pro.return_value.astream = _empty_aiter
            resp = await client.post("/analyze/AAPL", json=_payload())
            assert resp.status_code == 200
            assert resp.json()["job_id"].startswith("job-")
            mock_free.assert_called_once()
            mock_pro.assert_not_called()
    finally:
        override_settings(None)  # type: ignore[arg-type]


async def test_post_with_valid_token_routes_to_pro_graph(client):
    override_settings(Settings(pro_tier_token="secret"))
    try:
        with (
            patch("app.routes.analysis.build_free_graph") as mock_free,
            patch("app.routes.analysis.build_orchestrator_graph") as mock_pro,
        ):
            mock_free.return_value = MagicMock()
            mock_free.return_value.astream = _empty_aiter
            mock_pro.return_value = MagicMock()
            mock_pro.return_value.astream = _empty_aiter
            resp = await client.post(
                "/analyze/AAPL",
                json=_payload(),
                headers={"X-Pro-Token": "secret"},
            )
            assert resp.status_code == 200
            assert resp.json()["job_id"].startswith("job-")
            mock_pro.assert_called_once()
            mock_free.assert_not_called()
    finally:
        override_settings(None)  # type: ignore[arg-type]
