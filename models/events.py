from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


@dataclass
class SSEMessage:
    """Raw SSE message ready to send over the wire."""

    event: str
    data: str


class PhaseEvent(BaseModel):
    """A graph node started or completed."""

    phase: str
    status: str
    data: dict[str, Any] | None = None

    def to_sse(self) -> SSEMessage:
        return SSEMessage(event="phase", data=self.model_dump_json())


class CheckpointEvent(BaseModel):
    """Graph paused at a human-in-the-loop checkpoint."""

    checkpoint: str
    message: str

    def to_sse(self) -> SSEMessage:
        return SSEMessage(event="checkpoint", data=self.model_dump_json())


class StreamEvent(BaseModel):
    """Token-by-token LLM streaming output."""

    phase: str
    token: str

    def to_sse(self) -> SSEMessage:
        return SSEMessage(event="stream", data=self.model_dump_json())


class DoneEvent(BaseModel):
    """Workflow completed."""

    job_id: str
    total_time: float

    def to_sse(self) -> SSEMessage:
        return SSEMessage(event="done", data=self.model_dump_json())


class ErrorEvent(BaseModel):
    """Node or graph-level error."""

    phase: str | None = None
    error: str

    def to_sse(self) -> SSEMessage:
        return SSEMessage(event="error", data=self.model_dump_json())


class LogEvent(BaseModel):
    """Progress log message from a graph node."""

    message: str
    phase: str | None = None

    def to_sse(self) -> SSEMessage:
        return SSEMessage(event="log", data=self.model_dump_json())
