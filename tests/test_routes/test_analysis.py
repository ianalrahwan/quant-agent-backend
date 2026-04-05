from unittest.mock import patch

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from app.main import create_app

MOCK_NARRATIVE = "Test narrative."
MOCK_RECS = (
    '[{"strategy":"test","direction":"long_vol","legs":[],'
    '"rationale":"t","estimated_greeks":{"delta":0},"risk_reward":"t"}]'
)


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@respx.mock
@patch("graphs.trader.nodes.trade_rec._call_claude", return_value=MOCK_RECS)
@patch("graphs.trader.nodes.synthesize._call_claude", return_value=MOCK_NARRATIVE)
async def test_analyze_returns_job_id(mock_s, mock_r, client):
    respx.route().mock(return_value=Response(200, json=[]))
    respx.post("https://api.voyageai.com/v1/embeddings").mock(
        return_value=Response(200, json={"data": [], "usage": {"total_tokens": 0}})
    )

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
