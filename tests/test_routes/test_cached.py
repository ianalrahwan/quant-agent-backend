from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from sse.bus import InMemorySSEBus


@pytest.fixture
def app():
    a = create_app()
    a.state.sse_bus = InMemorySSEBus()
    a.state.session_factory = MagicMock()
    return a


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@patch("app.routes.cached.get_cached_analysis")
async def test_cached_found(mock_get, client):
    mock_row = MagicMock()
    mock_row.symbol = "SPY"
    mock_row.narrative = "Test narrative"
    mock_row.trade_recs = [{"strategy": "straddle"}]
    mock_row.vol_surface = {"regime": "flat"}
    mock_row.phases_log = ["log1"]
    mock_row.total_time = 23.5
    mock_row.scanner_signals = {"composite": 0.7}
    mock_row.created_at = datetime(2026, 4, 6, 12, 0, 0, tzinfo=UTC)
    mock_row.tier = "pro"
    mock_get.return_value = mock_row
    resp = await client.get("/cached/SPY")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "SPY"
    assert data["narrative"] == "Test narrative"
    assert data["tier"] == "pro"


@patch("app.routes.cached.get_cached_analysis")
async def test_cached_not_found(mock_get, client):
    mock_get.return_value = None
    resp = await client.get("/cached/UNKNOWN")
    assert resp.status_code == 404
