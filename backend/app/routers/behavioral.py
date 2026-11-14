from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from .. import examples as ex
from ..datafiles import DataBundle
from ..db.session import get_session
from ..deps import CREW, ERRORS, crew_access, get_data, roles
from ..schemas import KeystrokeBatch, KeystrokeResult, KeystrokeSummary, PvtResult, PvtSubmit, User
from ..services import behavioral as behavioral_service
from ..services.events import publish_all

router = APIRouter(tags=["5. Typing and reaction test"])
E = {k: ERRORS[k] for k in (401, 403, 404, 422)}


@router.post(
    "/crew/{crew_id}/keystrokes/batches",
    response_model=KeystrokeResult,
    summary="Send a batch of key presses",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def post_keystrokes(
    crew_id: str,
    body: KeystrokeBatch,
    user: User = Depends(crew_access),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """**Privacy: send only the timings and the key class, never the character.** The backend rejects with 422 any
    extra field (e.g. `key`, `code`, `text`).

    Frontend: collect the `keydown`/`keyup` events and send a batch every ~5 seconds or every 200 keys, with the
    same `session_id` while the user keeps typing in the same field. The response holds the cumulative features of
    the session, so you can show it directly in the live bars.

    The first sessions build the baseline: while `baseline_ready` is `false`, `status` is `unknown`. A session is
    judged only after its first 30 keys.

    **SSE:** `alert.created` (or `alert.updated`) and `dashboard.changed` when the deviation crosses the threshold."""
    result, events = await behavioral_service.add_batch(session, data, crew_id, body)
    publish_all(events)
    return result


@router.get(
    "/crew/{crew_id}/keystrokes/summary",
    response_model=KeystrokeSummary,
    summary="Typing summary",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def keystroke_summary(
    crew_id: str,
    last: int = Query(default=10, ge=1, le=100, description="How many recent sessions to return."),
    user: User = Depends(crew_access),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """The personal baseline, the latest session and the recent sessions. For the "Your rhythm" card and the
    comparison in the demo."""
    return await behavioral_service.summary(session, data, crew_id, last)


@router.post(
    "/crew/{crew_id}/pvt",
    response_model=PvtResult,
    status_code=201,
    summary="Send a reaction test (PVT-B)",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def post_pvt(crew_id: str, body: PvtSubmit, user: User = Depends(crew_access)):
    """The 3-minute test runs entirely in the frontend; send all the trials here at the end.

    The backend computes the mean 1/RT, the lapses (RT ≥ 355 ms) and the deviation from the baseline. The first
    2–3 tests are practice and do not enter the baseline.

    **SSE:** `dashboard.changed`."""
    return ex.PVT.model_copy(update={"crew_id": crew_id})


@router.get(
    "/crew/{crew_id}/pvt",
    response_model=list[PvtResult],
    summary="Reaction test history",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def list_pvt(crew_id: str, limit: int = Query(default=20, ge=1, le=200), user: User = Depends(crew_access)):
    return [ex.PVT.model_copy(update={"crew_id": crew_id})]
