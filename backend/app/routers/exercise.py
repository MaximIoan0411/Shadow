from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..datafiles import DataBundle
from ..db.session import get_session
from ..deps import CREW, ERRORS, crew_access, get_data, roles
from ..schemas import ExerciseSession, ExerciseSessionCreate, ExerciseToday, User
from ..services import exercise as exercise_service
from ..services.events import publish_all

router = APIRouter(tags=["6. Exercise"])
E = {k: ERRORS[k] for k in (401, 403, 404, 422)}


@router.get(
    "/crew/{crew_id}/exercise/today",
    response_model=ExerciseToday,
    summary="Today's exercise plan",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def exercise_today(
    crew_id: str,
    user: User = Depends(crew_access),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """The planned and completed sessions, the loading score, the recommendation to split into two sessions, the
    streak and the bone projection (an estimate)."""
    return await exercise_service.today(session, data, crew_id)


@router.post(
    "/crew/{crew_id}/exercise/sessions",
    response_model=ExerciseSession,
    status_code=201,
    summary="Log an exercise session",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def create_session(
    crew_id: str,
    body: ExerciseSessionCreate,
    user: User = Depends(crew_access),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """In the real version the log comes from the device. In the prototype the simulator or the astronaut sends it.

    **SSE:** `dashboard.changed`."""
    result, events = await exercise_service.create(session, data, crew_id, body)
    publish_all(events)
    return result


@router.get(
    "/crew/{crew_id}/exercise/sessions",
    response_model=list[ExerciseSession],
    summary="Session history",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def list_sessions(
    crew_id: str,
    from_day: int = Query(default=1, ge=1),
    to_day: int = Query(default=140, ge=1),
    user: User = Depends(crew_access),
    session: AsyncSession = Depends(get_session),
):
    """The sessions in the interval, newest first."""
    return await exercise_service.history(session, crew_id, from_day, to_day)
