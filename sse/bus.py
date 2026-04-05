import asyncio
import json
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import AsyncGenerator

import redis.asyncio as redis

from models.events import SSEMessage


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
    """In-memory SSE bus for testing. No Redis dependency."""

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[SSEMessage]]] = defaultdict(list)

    async def publish(self, job_id: str, message: SSEMessage) -> None:
        for queue in self._queues[job_id]:
            await queue.put(message)

    async def subscribe(self, job_id: str) -> AsyncGenerator[SSEMessage, None]:
        queue: asyncio.Queue[SSEMessage] = asyncio.Queue()
        self._queues[job_id].append(queue)
        try:
            while True:
                msg = await queue.get()
                yield msg
        finally:
            self._queues[job_id].remove(queue)
