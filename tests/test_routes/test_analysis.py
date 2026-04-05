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


async def test_analyze_returns_job_id(client):
    resp = await client.post(
        "/analyze/AAPL",
        json={
            "scanner_signals": {
                "iv_percentile": 0.85,
                "skew_kurtosis": 0.6,
                "dealer_gamma": -0.3,
                "term_structure": 0.9,
                "vanna": 0.7,
                "charm": 0.4,
                "composite": 0.72,
            },
            "auto_run": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert isinstance(data["job_id"], str)
    assert len(data["job_id"]) > 0


async def test_analyze_auto_run_default_false(client):
    resp = await client.post(
        "/analyze/TSLA",
        json={
            "scanner_signals": {
                "iv_percentile": 0.5,
                "skew_kurtosis": 0.5,
                "dealer_gamma": 0.0,
                "term_structure": 0.5,
                "vanna": 0.5,
                "charm": 0.5,
                "composite": 0.5,
            },
        },
    )
    assert resp.status_code == 200
    assert "job_id" in resp.json()
