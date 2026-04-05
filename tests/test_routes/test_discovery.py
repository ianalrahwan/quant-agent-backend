import respx
import pytest
from httpx import ASGITransport, AsyncClient, Response

from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@respx.mock
async def test_discover_returns_run_id_and_triggers_graph(client):
    respx.get("https://financialmodelingprep.com/api/v3/earning_call_transcript/AAPL").mock(
        return_value=Response(200, json=[])
    )
    respx.get("https://newsapi.org/v2/everything").mock(
        return_value=Response(200, json={"status": "ok", "articles": []})
    )
    respx.route().mock(return_value=Response(200, text=""))

    resp = await client.post(
        "/discover",
        json={
            "target_tickers": ["AAPL"],
            "source_types": ["earnings"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert data["run_id"].startswith("discovery-")


async def test_discover_all_defaults(client):
    resp = await client.post("/discover", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
