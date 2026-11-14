from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..datafiles import DataBundle
from ..db.session import get_session
from ..deps import CREW, ERRORS, crew_access, get_data, require_roles, roles
from ..schemas import CrewSummary, Dashboard, MetricSeries, Pillar, PillarDetail, Role, Timeline, User
from ..services import crew as crew_service

router = APIRouter(tags=["3. Crew and the interactive body"])
E = {k: ERRORS[k] for k in (401, 403, 404)}

AS_OF = Query(
    default=None,
    ge=1,
    description="Timeline scrubber: the state at the end of this day. Without it = now. "
    "Must be ≤ the current day (future days do not exist yet) → otherwise 422.",
)


@router.get(
    "/crew",
    response_model=list[CrewSummary],
    summary="Crew list",
    responses={k: ERRORS[k] for k in (401, 403)},
    openapi_extra=roles(Role.cmo),
)
async def list_crew(user: User = Depends(require_roles(Role.cmo)), session: AsyncSession = Depends(get_session)):
    """For the crew medical officer only. Holds only the overall status, no medical values."""
    return await crew_service.crew_list(session)


@router.get(
    "/crew/{crew_id}/dashboard",
    response_model=Dashboard,
    summary="The astronaut's dashboard",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def dashboard(
    crew_id: str,
    as_of_day: int | None = AS_OF,
    user: User = Depends(crew_access),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """**The main call of the astronaut's screen.** In one response: the state of the 4 pillars (the colours of the
    body zones), the perception gap, the cross signals, the main alert, the streaks and the reminders.

    Reload it when you get SSE `dashboard.changed`, `alert.created` or `alert.updated`."""
    return await crew_service.dashboard(session, data, crew_id, as_of_day)


@router.get(
    "/crew/{crew_id}/pillars/{pillar}",
    response_model=PillarDetail,
    summary="The panel of a body zone",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def pillar_detail(
    crew_id: str,
    pillar: Pillar,
    as_of_day: int | None = AS_OF,
    user: User = Depends(crew_access),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """Called on a click on a zone. Holds, in display order: the function of the body part, the space hazard,
    the values against the baseline, the chart, the explanation, the action plan and the sources."""
    return await crew_service.pillar_detail(session, data, crew_id, pillar, as_of_day)


@router.get(
    "/crew/{crew_id}/pillars/{pillar}/series",
    response_model=MetricSeries,
    summary="The series of a metric (chart)",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def pillar_series(
    crew_id: str,
    pillar: Pillar,
    metric: str = Query(description="The metric key, e.g. `night_pulse_bpm`. See README, “Metric keys”."),
    from_day: int = Query(default=1, ge=1),
    to_day: int | None = Query(default=None, ge=1, description="Default: the current day."),
    user: User = Depends(crew_access),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """For a second chart or for a longer interval than the panel's (which has the last 10 days)."""
    return await crew_service.series(session, data, crew_id, pillar, metric, from_day, to_day)


@router.get(
    "/crew/{crew_id}/timeline",
    response_model=Timeline,
    summary="History by day (timeline scrubber)",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def get_timeline(
    crew_id: str,
    from_day: int = Query(default=1, ge=1),
    to_day: int | None = Query(default=None, ge=1, description="Default and maximum: the current day."),
    user: User = Depends(crew_access),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """The state of every pillar on every day **that has happened**: from `from_day` to the current day (the
    mission starts on day 96, so at first there are 96 days). Future days are not included; the scrubber shows the
    rest up to `total_days` (from `/mission`) as "not yet".

    Load it once at startup and reload it on `mission.tick` only when `mission_day` changes.
    When the user stops on a day, reload `dashboard` and the open panel with `?as_of_day=`."""
    return await crew_service.timeline(session, data, crew_id, from_day, to_day)
