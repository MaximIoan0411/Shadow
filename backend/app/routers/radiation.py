from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..datafiles import DataBundle
from ..db.session import get_session
from ..deps import ALL, CREW, ERRORS, current_user, get_data, require_roles, roles
from ..schemas import RadiationSeries, RadiationStatus, SepEvent, ShelterAck, User
from ..services import radiation as radiation_service
from ..services.events import publish_all

router = APIRouter(prefix="/radiation", tags=["9. Radiation and the solar storm"])


@router.get(
    "/status",
    response_model=RadiationStatus,
    summary="Radiation now",
    responses={k: ERRORS[k] for k in (401, 403)},
    openapi_extra=roles(*CREW),
)
async def radiation_status(
    user: User = Depends(require_roles(*CREW)),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """The dose rate at the on-board dosimeter, the 24-h mean, whether there is an alert and whether the crew is in
    the shelter.

    `lead_minutes` is filled in when the DONKI warning from Earth arrives: the number of minutes SHADOW was faster.
    Show it big; it is the number in the pitch.

    The `earth` role has NO access: Earth does not see the ship's dosimeter in real time, only what comes through
    the queue."""
    return await radiation_service.status(session, data, user)


@router.get(
    "/series",
    response_model=RadiationSeries,
    summary="The dose curve (chart)",
    responses={k: ERRORS[k] for k in (401, 403)},
    openapi_extra=roles(*CREW),
)
async def radiation_series(
    hours: float = Query(default=24, gt=0, le=240, description="How many mission hours back."),
    step_min: int = Query(default=10, ge=1, le=120),
    user: User = Depends(require_roles(*CREW)),
    session: AsyncSession = Depends(get_session),
):
    """The points of the dose chart. Reload on SSE `radiation.reading` (at most once every 2 real seconds)."""
    return await radiation_service.series(session, hours, step_min)


@router.get(
    "/events",
    response_model=list[SepEvent],
    summary="The available DONKI events",
    responses={401: ERRORS[401]},
    openapi_extra=roles(*ALL),
)
async def radiation_events(user: User = Depends(current_user), data: DataBundle = Depends(get_data)):
    """The real NASA DONKI events loaded from the file (offline). For now one: 11 May 2024."""
    return [radiation_service.sep_event(data, None)]


@router.post(
    "/shelter-ack",
    response_model=RadiationStatus,
    summary='"I am in the shelter"',
    responses={k: ERRORS[k] for k in (401, 403, 422)},
    openapi_extra=roles(*CREW),
)
async def shelter_ack(
    body: ShelterAck,
    user: User = Depends(require_roles(*CREW)),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """The astronaut confirms they reached the shelter (or left it). From then on the simulator applies the
    shielding factor, and the time is saved.

    **SSE:** `radiation.reading`."""
    result, events = await radiation_service.shelter(session, data, body.sheltered, user)
    publish_all(events)
    return result
