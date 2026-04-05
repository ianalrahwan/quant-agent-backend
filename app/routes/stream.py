from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from sse.bus import SSEBus

router = APIRouter()


class ResumeRequest(BaseModel):
    checkpoint: str
    user_input: dict[str, Any] | None = None


def _get_bus(request: Request) -> SSEBus:
    return request.app.state.sse_bus


@router.get("/stream/{job_id}")
async def stream(job_id: str, request: Request) -> StreamingResponse:
    """SSE endpoint that streams graph events for a job."""
    bus = _get_bus(request)

    async def event_generator():
        async for msg in bus.subscribe(job_id):
            yield f"event: {msg.event}\ndata: {msg.data}\n\n"
            if msg.event == "done" or msg.event == "error":
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/stream/{job_id}/resume")
async def resume(job_id: str, request_body: ResumeRequest) -> dict:
    """Resume a graph from a checkpoint.

    Stub: acknowledges the resume but does not trigger graph execution yet.
    Will be wired to LangGraph checkpoint resume in Plan 3/4.
    """
    return {
        "status": "resumed",
        "job_id": job_id,
        "checkpoint": request_body.checkpoint,
    }
