import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from models.events import DoneEvent, PhaseEvent
from sse.bus import InMemorySSEBus


@pytest.fixture
def bus():
    return InMemorySSEBus()


@pytest.fixture
def app(bus):
    application = create_app()
    # Override the SSE bus dependency
    application.state.sse_bus = bus
    return application


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_stream_receives_sse_events(client, bus):
    job_id = "job-test-001"

    async def publish_events():
        await asyncio.sleep(0.05)
        await bus.publish(job_id, PhaseEvent(phase="vol_surface", status="complete").to_sse())
        await bus.publish(job_id, DoneEvent(job_id=job_id, total_time=1.0).to_sse())

    asyncio.create_task(publish_events())

    resp = await client.get(f"/stream/{job_id}", timeout=5.0)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    # Parse SSE lines
    lines = resp.text.strip().split("\n")
    events = [line for line in lines if line.startswith("event:")]
    assert len(events) >= 2
    assert "event: phase" in events[0]
    assert "event: done" in events[1]


async def test_resume_checkpoint(client):
    job_id = "job-test-002"
    resp = await client.post(
        f"/stream/{job_id}/resume",
        json={"checkpoint": "vol_surface_review", "user_input": {"proceed": True}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resumed"
