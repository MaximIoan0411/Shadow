from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..datafiles import DataBundle
from ..db.session import get_session
from ..deps import CREW, ERRORS, crew_access, current_user, get_data, require_roles, roles
from ..schemas import (
    Alert,
    AlertBrief,
    AlertState,
    AlertTopic,
    EscalateRequest,
    Recommendation,
    ResolveRequest,
    Role,
    StepUpdate,
    User,
)
from ..services import access
from ..services import alerts as alerts_service
from ..services.events import publish_all

router = APIRouter(tags=["7. Alerts, triage, catalog"])
E = {k: ERRORS[k] for k in (401, 403, 404, 422)}
E409 = {**E, 409: ERRORS[409]}


@router.get(
    "/crew/{crew_id}/alerts",
    response_model=list[AlertBrief],
    summary="A crew member's alerts",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def list_alerts(
    crew_id: str,
    state: AlertState | None = Query(default=None, description="Filter. Without it = all unresolved alerts."),
    topic: AlertTopic | None = None,
    user: User = Depends(crew_access),
    session: AsyncSession = Depends(get_session),
):
    """Short list, most severe first. The crew medical officer only gets level ≥ 2 alerts of other members here."""
    return await alerts_service.list_for_crew(session, crew_id, user, state, topic)


@router.get(
    "/cmo/queue",
    response_model=list[AlertBrief],
    summary="Crew medical officer's queue",
    responses={k: ERRORS[k] for k in (401, 403)},
    openapi_extra=roles(Role.cmo),
)
async def cmo_queue(user: User = Depends(require_roles(Role.cmo)), session: AsyncSession = Depends(get_session)):
    """All unresolved level 2 and 3 alerts across the crew. The main screen of the `cmo` role."""
    return await alerts_service.cmo_queue(session)


@router.get("/alerts/{alert_id}", response_model=Alert, summary="Full alert", responses=E, openapi_extra=roles(*CREW))
async def get_alert(
    alert_id: str,
    user: User = Depends(require_roles(*CREW)),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """The evidence, the cause (individual or environmental), the catalog recommendation with its source, the action
    plan, the recheck date and the history. Every read by the crew medical officer is written to the access log."""
    a = await alerts_service.get_row(session, alert_id, user)
    if user.role == Role.cmo:
        await access.record(
            session, user, action="read_alert", resource=f"alerts/{alert_id}", crew_id=a.crew_id, outcome="allowed"
        )
        await session.commit()
    return alerts_service.to_schema(a, data)


@router.post(
    "/alerts/{alert_id}/ack",
    response_model=Alert,
    summary="Confirm you have seen the alert",
    responses=E409,
    openapi_extra=roles(Role.astronaut, Role.cmo),
)
async def ack_alert(
    alert_id: str,
    user: User = Depends(require_roles(*CREW)),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """Moves the alert from `active` to `acknowledged`. Not allowed on an alert that is already escalated or
    resolved (409 `invalid_state`).

    **SSE:** `alert.updated`."""
    alert, events = await alerts_service.acknowledge(session, data, alert_id, user)
    publish_all(events)
    return alert


@router.put(
    "/alerts/{alert_id}/plan/steps/{step_id}",
    response_model=Alert,
    summary="Tick a plan step",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def update_step(
    alert_id: str,
    step_id: str,
    body: StepUpdate,
    user: User = Depends(require_roles(*CREW)),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """Ticks or unticks a step of the action plan.

    **SSE:** `alert.updated`."""
    alert, events = await alerts_service.update_step(session, data, alert_id, step_id, body.done, user)
    publish_all(events)
    return alert


@router.post(
    "/alerts/{alert_id}/escalate",
    response_model=Alert,
    summary="Escalate the alert",
    responses=E409,
    openapi_extra=roles(*CREW),
)
async def escalate(
    alert_id: str,
    body: EscalateRequest,
    user: User = Depends(require_roles(*CREW)),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """Raises the alert by one level.

    * `to_level = 2` — the astronaut sends it to the crew medical officer. It shows up in `/cmo/queue`.
    * `to_level = 3` — **only the `cmo` role**. The backend automatically creates a signed and encrypted packet in
      the queue to Earth and puts its id in `packet_id`. There is no need to call `/link/outbox`.

    The level can never go down (409 `invalid_state`). Critical alerts can also be escalated automatically by the
    triage engine.

    **SSE:** `alert.updated`, and at level 3 also `packet.sent` when the window opens."""
    alert, events = await alerts_service.escalate(session, data, alert_id, body.to_level, body.note, user)
    publish_all(events)
    return alert


@router.post(
    "/alerts/{alert_id}/resolve",
    response_model=Alert,
    summary="Close the alert",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def resolve(
    alert_id: str,
    body: ResolveRequest,
    user: User = Depends(require_roles(*CREW)),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """An astronaut can close level 1 alerts; level 2 and 3 alerts are closed by the crew medical officer.
    `outcome = monitoring` keeps the alert open and moves `recheck_at` by one more day.

    **SSE:** `alert.updated`."""
    alert, events = await alerts_service.resolve(session, data, alert_id, body.outcome, body.note, user)
    publish_all(events)
    return alert


@router.get(
    "/catalog/recommendations",
    response_model=list[Recommendation],
    summary="Recommendation catalog",
    responses={401: ERRORS[401]},
    openapi_extra=roles(*CREW, Role.earth),
)
async def list_recommendations(
    topic: AlertTopic | None = None,
    level: int | None = Query(default=None, ge=1, le=3),
    user: User = Depends(current_user),
    data: DataBundle = Depends(get_data),
):
    """Recommendations written by the team based on the NASA HRP risks, each with its source. The AI doctor only
    rephrases them."""
    return alerts_service.recommendations(data, topic, level)


@router.get(
    "/catalog/recommendations/{rec_id}",
    response_model=Recommendation,
    summary="One catalog recommendation",
    responses={k: ERRORS[k] for k in (401, 404)},
    openapi_extra=roles(*CREW, Role.earth),
)
async def get_recommendation(rec_id: str, user: User = Depends(current_user), data: DataBundle = Depends(get_data)):
    return alerts_service.recommendation(data, rec_id)
