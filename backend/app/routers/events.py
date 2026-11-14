import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from .. import examples as ex
from ..deps import ALL, ERRORS, current_user, roles, sse_format, subscribe, unsubscribe
from ..schemas import Role, User

router = APIRouter(tags=["13. Evenimente live (SSE)"])


@router.get("/events", summary="Fluxul de evenimente live", responses={401: ERRORS[401], 200: {"content": {"text/event-stream": {}}, "description": "Flux SSE. Fiecare mesaj are `event: <type>` și `data: <SseEvent JSON>`."}},
            response_class=StreamingResponse, openapi_extra=roles(*ALL))
async def events(request: Request, user: User = Depends(current_user)):
    """Conexiune Server-Sent Events, ținută deschisă cât e aplicația pornită. **Înlocuiește polling-ul.**

    * Autentificare cu același antet `Authorization`. `EventSource` din browser nu poate trimite antete, deci folosiți
      `@microsoft/fetch-event-source` (exemplu în README).
    * Fiecare utilizator primește doar evenimentele la care are dreptul: astronautul doar pe ale lui și pe cele
      generale; `earth` doar `mission.tick`, `environment.changed` și `packet.*`.
    * La 15 secunde fără evenimente vine un comentariu `: ping`, ca să nu se închidă conexiunea.
    * La reconectare, reîncărcați datele ecranului curent; evenimentele pierdute nu se retrimit.

    Lista tipurilor și forma câmpului `data` pentru fiecare: README, secțiunea „Evenimente live”."""
    q = subscribe()

    async def gen():
        try:
            n = 0
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(q.get(), timeout=3)
                    if user.role == Role.astronaut and event.get("crew_id") not in (None, user.crew_id):
                        continue
                    if user.role == Role.earth and not event["type"].startswith(("packet.", "mission.", "environment.")):
                        continue
                    yield sse_format(event)
                except TimeoutError:
                    n += 1
                    yield sse_format({"id": f"tick-{n}", "type": "mission.tick", "at": ex.NOW.isoformat(), "crew_id": None,
                                      "data": {"sim_now": ex.MISSION.sim_now.isoformat(), "mission_day": ex.MISSION.mission_day}})
        finally:
            unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
