from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..datafiles import DataBundle
from ..db.session import get_session
from ..deps import ALL, CREW, ERRORS, current_user, get_data, require_roles, roles
from ..schemas import ClockUpdate, EnvironmentInfo, EnvironmentUpdate, MissionState, User
from ..services import mission as mission_service
from ..services.events import Event, publish_all

router = APIRouter(tags=["2. Mission, environment, clock"])


@router.get(
    "/mission",
    response_model=MissionState,
    summary="Mission state",
    responses={401: ERRORS[401]},
    openapi_extra=roles(*ALL),
)
async def get_mission(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """Mission time (SimClock), current day, environment and the state of the link with Earth.

    The mission starts on **day 96 at 07:00** (days 1–95 are history generated when the server starts), with time
    sped up `time_scale` times (default ×60: one mission day = 24 real minutes).

    Call it once at startup. After that, the time comes through SSE (`mission.tick`), not through polling."""
    return await mission_service.state(session, data)


@router.get(
    "/environments",
    response_model=list[EnvironmentInfo],
    summary="List of environments",
    responses={401: ERRORS[401]},
    openapi_extra=roles(*ALL),
)
async def list_environments(user: User = Depends(current_user), data: DataBundle = Depends(get_data)):
    """The 4 environments for the switch: station, Moon, transit to Mars, base on Mars."""
    return mission_service.environments(data)


@router.put(
    "/mission/environment",
    response_model=MissionState,
    summary="Change the environment",
    responses={k: ERRORS[k] for k in (401, 403, 422)},
    openapi_extra=roles(*CREW),
)
async def set_environment(
    body: EnvironmentUpdate,
    user: User = Depends(require_roles(*CREW)),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """The environment switch. Changes the link delay, the background dose rate and the gravity-dependent thresholds.

    **Effects:** packets already `in_transit` keep their arrival time; new ones use the new delay.
    **SSE:** `environment.changed` with the new `MissionState`."""
    new_state, events = await mission_service.set_environment(session, data, body.environment)
    publish_all(events)
    return new_state


@router.put(
    "/sim/clock",
    response_model=MissionState,
    summary="Change the clock speed or day (demo)",
    responses={k: ERRORS[k] for k in (401, 403, 409, 422)},
    openapi_extra=roles(*CREW),
)
async def set_clock(
    body: ClockUpdate,
    user: User = Depends(require_roles(*CREW)),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """Demo only.

    * `time_scale` changes the speed; the current mission time stays the same.
    * `mission_day` jumps **forward** to the start of that day (07:00): the backend generates the missing days with
      the simulator and runs the engine over them, so new alerts can appear. **Going back is not possible** (409
      `invalid_state`); for a rehearsal from the start use `POST /sim/reset`.

    The timeline scrubber does NOT use this endpoint: it only reads the history with `?as_of_day=`.

    **SSE:** `mission.tick` with the new day, then `dashboard.changed` and possibly `alert.created`."""
    before = (await mission_service.state(session, data)).mission_day
    state = await mission_service.set_clock(session, data, time_scale=body.time_scale, mission_day=body.mission_day)
    events = [Event("mission.tick", mission_service.tick_data())]
    if state.mission_day > before:
        events.append(Event("dashboard.changed", {"reason": "jump"}))
    publish_all(events)
    return state
