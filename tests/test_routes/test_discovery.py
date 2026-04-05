import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_discover_returns_run_id(client):
    resp = await client.post(
        "/discover",
        json={
            "target_tickers": ["AAPL", "TSLA"],
            "source_types": ["earnings", "news"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data


async def test_discover_all_defaults(client):
    resp = await client.post("/discover", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
