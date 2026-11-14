from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..datafiles import DataBundle
from ..db.session import get_session
from ..deps import CREW, ERRORS, crew_access, current_user, get_data, roles
from ..schemas import Checkin, CheckinCreate, CheckinResult, CheckinSchema, User
from ..services import checkins as checkins_service
from ..services.events import publish_all

router = APIRouter(tags=["4. Check-in"])
E = {k: ERRORS[k] for k in (401, 403, 404, 422)}


@router.get(
    "/checkin/schema",
    response_model=CheckinSchema,
    summary="Check-in fields",
    responses={401: ERRORS[401]},
    openapi_extra=roles(*CREW),
)
async def checkin_schema(user: User = Depends(current_user), data: DataBundle = Depends(get_data)):
    """The list of fields, with the "How to measure", "What it means" and "Why it matters in space" texts and the
    plausibility limits (`min`/`max`). The frontend builds the form from this response; do not keep the texts in code."""
    return checkins_service.schema(data)


@router.post(
    "/crew/{crew_id}/checkins",
    response_model=CheckinResult,
    status_code=201,
    summary="Send the morning check-in",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def create_checkin(
    crew_id: str,
    body: CheckinCreate,
    user: User = Depends(crew_access),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """Saves the check-in of the day. **One check-in per mission day**: a second one replaces the first.

    What the backend does, in order:
    1. checks every field against `min`/`max` from the schema; impossible fields do NOT give a 422 error, they show
       up in `rejected` and are saved as `null` (the rest of the check-in stays valid);
    2. compares the values with the personal baseline;
    3. recomputes the perception gap;
    4. runs triage and creates alerts, if needed;
    5. updates the streak.

    **SSE:** `dashboard.changed`, plus `alert.created` for every new alert."""
    result, events = await checkins_service.create(session, data, crew_id, body)
    publish_all(events)
    return result


@router.get(
    "/crew/{crew_id}/checkins",
    response_model=list[Checkin],
    summary="Check-in history",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def list_checkins(
    crew_id: str,
    from_day: int = Query(default=1, ge=1),
    to_day: int = Query(default=140, ge=1),
    user: User = Depends(crew_access),
    session: AsyncSession = Depends(get_session),
):
    """The check-ins in the interval, newest first."""
    return await checkins_service.history(session, crew_id, from_day, to_day)


@router.get(
    "/crew/{crew_id}/checkins/today",
    response_model=Checkin | None,
    summary="Today's check-in",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def today_checkin(crew_id: str, user: User = Depends(crew_access), session: AsyncSession = Depends(get_session)):
    """Returns the check-in of the current day, or `null` if it has not been done. Use it to decide whether to show
    the form."""
    return await checkins_service.today(session, crew_id)
