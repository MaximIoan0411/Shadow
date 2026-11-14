from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .. import examples as ex
from ..datafiles import DataBundle
from ..db.session import get_session
from ..deps import CREW, ERRORS, get_data, publish, require_roles, roles
from ..schemas import Ok, Packet, RadiationStatus, Rejection, Role, SepStart, User
from ..security import lockout
from ..services import radiation as radiation_service
from ..services.events import publish_all

router = APIRouter(tags=["12. Demo and simulator"])
E = {k: ERRORS[k] for k in (401, 403, 422)}


@router.post(
    "/sim/sep/start",
    response_model=RadiationStatus,
    summary="Start the solar storm",
    responses=E,
    openapi_extra=roles(*CREW, Role.earth),
)
async def sep_start(
    body: SepStart,
    user: User = Depends(require_roles(*CREW, Role.earth)),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """The demo button. The simulator replays the real event from DONKI:

    1. the dose rate at the dosimeter rises → after 3 readings above 2× the mean, SHADOW gives the level 1 alert
       (`radiation.alert`);
    2. Earth's warning leaves the queue as a `donki_alert` packet, direction `up`, at the time of NASA's alert
       (20 minutes after the onset), and arrives after the link delay;
    3. on arrival, `lead_minutes` is filled in in `/radiation/status`.

    **SSE:** `radiation.alert`, `alert.created`, `radiation.reading`, `packet.sent`, then `packet.arrived`."""
    status, events = await radiation_service.start_storm(session, data, body.event_id, body.starts_in_min)
    publish_all(events)
    return status


@router.post(
    "/sim/sep/stop",
    response_model=RadiationStatus,
    summary="Stop the solar storm",
    responses=E,
    openapi_extra=roles(*CREW, Role.earth),
)
async def sep_stop(
    user: User = Depends(require_roles(*CREW, Role.earth)),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """Brings the dose rate back to the background. **SSE:** `radiation.cleared`."""
    status, events = await radiation_service.stop_storm(session, data)
    publish_all(events)
    return status


@router.post(
    "/demo/inject-spoof",
    response_model=Packet,
    summary="Inject a forged packet",
    responses=E,
    openapi_extra=roles(*CREW, Role.earth),
)
async def inject_spoof(user: User = Depends(require_roles(*CREW, Role.earth))):
    """Security demo: puts in the queue a packet signed with a wrong key. On arrival it is rejected and shows up with
    `status = rejected`, `signature_valid = false`, in the log and in `/security/rejections`.

    **SSE:** `packet.rejected`."""
    p = link_packet(ex.PACKETS[2])
    publish("packet.rejected", p)
    return p


@router.post(
    "/demo/frozen-sensor",
    response_model=Rejection,
    summary="Simulate a frozen sensor",
    responses=E,
    openapi_extra=roles(*CREW, Role.earth),
)
async def frozen_sensor(user: User = Depends(require_roles(*CREW, Role.earth))):
    """Security demo: the simulator sends the same value many times; the validation layer rejects it.

    **SSE:** `measurement.rejected`."""
    publish("measurement.rejected", ex.REJECTIONS[1], ex.REJECTIONS[1].crew_id)
    return ex.REJECTIONS[1]


@router.post(
    "/sim/reset",
    response_model=Ok,
    summary="Bring the demo back to the start",
    responses=E,
    openapi_extra=roles(*CREW, Role.earth),
)
async def reset(user: User = Depends(require_roles(*CREW, Role.earth))):
    """Removes everything changed during the demo and reloads the scenario: the database is recreated, the history is
    regenerated (same seed, so the same data), the clock restarts on day 96 at 07:00, and the account lockouts are
    cleared. It takes a few seconds. Use it between rehearsals.

    After a reset the frontend must reload everything (as after a reconnect). Tokens stay valid.

    **SSE:** `mission.tick` with day 96, then `dashboard.changed`."""
    lockout.reset_all()
    publish("dashboard.changed", {"reason": "reset"})
    return Ok()


def link_packet(p) -> Packet:
    return Packet(**p.model_dump(include=set(Packet.model_fields)))
