import asyncio

import pytest

from models.events import DoneEvent, PhaseEvent
from sse.bus import InMemorySSEBus


@pytest.fixture
def bus() -> InMemorySSEBus:
    return InMemorySSEBus()


async def test_publish_and_subscribe(bus: InMemorySSEBus):
    job_id = "job-123"
    received: list = []

    async def collect():
        async for msg in bus.subscribe(job_id):
            received.append(msg)
            if msg.event == "done":
                break

    task = asyncio.create_task(collect())

    # Small delay to let subscriber start
    await asyncio.sleep(0.01)

    event1 = PhaseEvent(phase="vol_surface", status="complete")
    event2 = DoneEvent(job_id=job_id, total_time=1.5)
    await bus.publish(job_id, event1.to_sse())
    await bus.publish(job_id, event2.to_sse())

    await asyncio.wait_for(task, timeout=2.0)

    assert len(received) == 2
    assert received[0].event == "phase"
    assert received[1].event == "done"


async def test_subscribe_only_receives_own_job(bus: InMemorySSEBus):
    received: list = []

    async def collect():
        async for msg in bus.subscribe("job-A"):
            received.append(msg)
            if msg.event == "done":
                break

    task = asyncio.create_task(collect())
    await asyncio.sleep(0.01)

    # Publish to different job — should not be received
    await bus.publish("job-B", PhaseEvent(phase="x", status="complete").to_sse())

    # Publish to our job
    await bus.publish("job-A", DoneEvent(job_id="job-A", total_time=1.0).to_sse())

    await asyncio.wait_for(task, timeout=2.0)

    assert len(received) == 1
    assert received[0].event == "done"
