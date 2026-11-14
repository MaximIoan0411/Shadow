from fastapi import APIRouter, Depends, Query

from .. import examples as ex
from ..deps import CREW, ERRORS, crew_access, publish, roles
from ..schemas import DataSource, ExerciseSession, ExerciseSessionCreate, ExerciseToday, User

router = APIRouter(tags=["6. Exerciții"])
E = {k: ERRORS[k] for k in (401, 403, 404, 422)}


@router.get("/crew/{crew_id}/exercise/today", response_model=ExerciseToday, summary="Planul de exerciții de azi", responses=E, openapi_extra=roles(*CREW))
async def exercise_today(crew_id: str, user: User = Depends(crew_access)):
    """Sesiunile planificate și făcute, scorul de încărcare, recomandarea de împărțire în două sesiuni și seria de zile."""
    return ex.EX_TODAY


@router.post("/crew/{crew_id}/exercise/sessions", response_model=ExerciseSession, status_code=201, summary="Înregistrează o sesiune de exerciții", responses=E, openapi_extra=roles(*CREW))
async def create_session(crew_id: str, body: ExerciseSessionCreate, user: User = Depends(crew_access)):
    """În versiunea reală, jurnalul vine de la aparat. În prototip îl trimite simulatorul sau astronautul, de mână.

    **SSE:** `dashboard.changed`."""
    publish("dashboard.changed", {"reason": "exercise"}, crew_id)
    return ExerciseSession(**body.model_dump(), id="ex-0212", crew_id=crew_id, mission_day=ex.MISSION.mission_day, loading_score=41, source=DataSource.manual)


@router.get("/crew/{crew_id}/exercise/sessions", response_model=list[ExerciseSession], summary="Istoricul sesiunilor", responses=E, openapi_extra=roles(*CREW))
async def list_sessions(crew_id: str, from_day: int = Query(default=1, ge=1), to_day: int = Query(default=140, ge=1), user: User = Depends(crew_access)):
    return [ex.EX_SESSION.model_copy(update={"crew_id": crew_id})]
