import asyncio
import json
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import AsyncGenerator
from contextvars import ContextVar

import redis.asyncio as redis

from models.events import SSEMessage

# Context var holding (bus, job_id) for the current background task
_bus_ctx: ContextVar[tuple["SSEBus", str] | None] = ContextVar("_bus_ctx", default=None)


def set_bus_context(bus: "SSEBus", job_id: str) -> None:
    """Set the SSE bus context for the current task."""
    _bus_ctx.set((bus, job_id))


async def emit(message: SSEMessage) -> None:
    """Publish an SSE event if a bus is in context. No-op otherwise."""
    ctx = _bus_ctx.get()
    if ctx is not None:
        bus, job_id = ctx
        await bus.publish(job_id, message)


class SSEBus(ABC):
    """Abstract interface for SSE event pub-sub."""

    @abstractmethod
    async def publish(self, job_id: str, message: SSEMessage) -> None: ...

    @abstractmethod
    async def subscribe(self, job_id: str) -> AsyncGenerator[SSEMessage, None]: ...


class RedisSSEBus(SSEBus):
    """Redis-backed SSE pub-sub for production."""

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    def _channel(self, job_id: str) -> str:
        return f"sse:{job_id}"

    async def publish(self, job_id: str, message: SSEMessage) -> None:
        payload = json.dumps({"event": message.event, "data": message.data})
        await self._redis.publish(self._channel(job_id), payload)

    async def subscribe(self, job_id: str) -> AsyncGenerator[SSEMessage, None]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self._channel(job_id))
        try:
            async for raw in pubsub.listen():
                if raw["type"] != "message":
                    continue
                parsed = json.loads(raw["data"])
                yield SSEMessage(event=parsed["event"], data=parsed["data"])
        finally:
            await pubsub.unsubscribe(self._channel(job_id))


class InMemorySSEBus(SSEBus):
    """In-memory SSE bus with event replay.

    Buffers all published events per job so late subscribers receive
    the full history before streaming new events.
    """

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[SSEMessage]]] = defaultdict(list)
        self._history: dict[str, list[SSEMessage]] = defaultdict(list)

    async def publish(self, job_id: str, message: SSEMessage) -> None:
        self._history[job_id].append(message)
        for queue in self._queues[job_id]:
            await queue.put(message)

    async def subscribe(self, job_id: str) -> AsyncGenerator[SSEMessage, None]:
        # Replay buffered events first
        for msg in self._history[job_id]:
            yield msg

        # Then stream new events via queue
        queue: asyncio.Queue[SSEMessage] = asyncio.Queue()
        self._queues[job_id].append(queue)
        try:
            while True:
                msg = await queue.get()
                yield msg
        finally:
            self._queues[job_id].remove(queue)
