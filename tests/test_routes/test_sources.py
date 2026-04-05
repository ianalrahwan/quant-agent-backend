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


async def test_sources_summary_returns_shape(client):
    resp = await client.get("/sources/AAPL/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert "sources" in data
    assert isinstance(data["sources"], dict)
    # Each source type should have last_updated and count
    for source_type in ["earnings", "news", "podcast", "cftc"]:
        assert source_type in data["sources"]
        assert "last_updated" in data["sources"][source_type]
        assert "count" in data["sources"][source_type]


async def test_sources_summary_uppercases_symbol(client):
    resp = await client.get("/sources/aapl/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
