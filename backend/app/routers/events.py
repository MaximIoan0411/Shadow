import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ..deps import ALL, ERRORS, current_user, roles, sse_format, subscribe, unsubscribe, visible_to
from ..schemas import User

router = APIRouter(tags=["13. Live events (SSE)"])

PING_AFTER_S = 15
PING = ": ping\n\n"


async def stream(
    user: User, queue: asyncio.Queue, is_disconnected: Callable[[], Awaitable[bool]], ping_after_s: float = PING_AFTER_S
) -> AsyncIterator[str]:
    try:
        while not await is_disconnected():
            try:
                event = await asyncio.wait_for(queue.get(), timeout=ping_after_s)
            except TimeoutError:
                yield PING
                continue
            if visible_to(user, event):
                yield sse_format(event)
    finally:
        unsubscribe(queue)


@router.get(
    "/events",
    summary="Live event stream",
    responses={
        401: ERRORS[401],
        200: {
            "content": {"text/event-stream": {}},
            "description": "SSE stream. Every message has `event: <type>` and `data: <SseEvent JSON>`.",
        },
    },
    response_class=StreamingResponse,
    openapi_extra=roles(*ALL),
)
async def events(request: Request, user: User = Depends(current_user)):
    """A Server-Sent Events connection, kept open while the app runs. **It replaces polling.**

    * Authentication with the same `Authorization` header. The browser's `EventSource` cannot send headers, so use
      `@microsoft/fetch-event-source` (example in the README).
    * Every user gets only the events they are allowed to see: an astronaut only their own and the general ones;
      `earth` only `mission.tick`, `environment.changed` and `packet.*`.
    * `mission.tick` comes every real second; after 15 seconds without events a `: ping` comment keeps the
      connection open.
    * On reconnect, reload the data of the current screen; missed events are not sent again.

    The list of types and the shape of `data` for each: README, section "Live events"."""
    q = subscribe()
    return StreamingResponse(
        stream(user, q, request.is_disconnected),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
