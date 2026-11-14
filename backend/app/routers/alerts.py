from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from .. import examples as ex
from ..db.session import get_session
from ..deps import CREW, ERRORS, ApiError, crew_access, current_user, publish, require_roles, roles
from ..schemas import (
    Alert,
    AlertBrief,
    AlertHistoryEntry,
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

router = APIRouter(tags=["7. Alerts, triage, catalog"])
E = {k: ERRORS[k] for k in (401, 403, 404, 422)}
E409 = {**E, 409: ERRORS[409]}


def _get(alert_id: str, user: User) -> Alert:
    a = ex.ALERTS.get(alert_id)
    if not a:
        raise ApiError(404, "not_found", f"Alert {alert_id} does not exist.")
    if user.role == Role.astronaut and a.crew_id != user.crew_id:
        raise ApiError(403, "forbidden", "You do not have access to another crew member's alert.")
    if user.role == Role.cmo and a.level < 2 and a.crew_id != user.crew_id:
        raise ApiError(403, "forbidden", "The crew medical officer only sees level 2 and 3 alerts.")
    return a


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
):
    """Short list, most severe first. The crew medical officer only gets level ≥ 2 alerts of other members here."""
    out = [
        ex.brief(a)
        for a in ex.ALERTS.values()
        if a.crew_id == crew_id and (state is None or a.state == state) and (topic is None or a.topic == topic)
    ]
    if user.role == Role.cmo and user.crew_id != crew_id:
        out = [a for a in out if a.level >= 2]
    return sorted(out, key=lambda a: -a.level)


@router.get(
    "/cmo/queue",
    response_model=list[AlertBrief],
    summary="Crew medical officer's queue",
    responses={k: ERRORS[k] for k in (401, 403)},
    openapi_extra=roles(Role.cmo),
)
async def cmo_queue(user: User = Depends(require_roles(Role.cmo))):
    """All unresolved level 2 and 3 alerts across the crew. The main screen of the `cmo` role."""
    return [ex.brief(a) for a in ex.ALERTS.values() if a.level >= 2 and a.state != AlertState.resolved]


@router.get("/alerts/{alert_id}", response_model=Alert, summary="Full alert", responses=E, openapi_extra=roles(*CREW))
async def get_alert(
    alert_id: str,
    user: User = Depends(require_roles(*CREW)),
    session: AsyncSession = Depends(get_session),
):
    """The evidence, the cause (individual or environmental), the catalog recommendation with its source, the action
    plan, the recheck date and the history. Every read by the crew medical officer is written to the access log."""
    a = _get(alert_id, user)
    if user.role == Role.cmo:
        await access.record(
            session, user, action="read_alert", resource=f"alerts/{alert_id}", crew_id=a.crew_id, outcome="allowed"
        )
        await session.commit()
    return a


@router.post(
    "/alerts/{alert_id}/ack",
    response_model=Alert,
    summary="Confirm you have seen the alert",
    responses=E409,
    openapi_extra=roles(Role.astronaut, Role.cmo),
)
async def ack_alert(alert_id: str, user: User = Depends(require_roles(*CREW))):
    """Moves the alert from `active` to `acknowledged`. Not allowed on an alert that is already escalated or
    resolved (409 `invalid_state`).

    **SSE:** `alert.updated`."""
    a = _get(alert_id, user)
    if a.state != AlertState.active:
        raise ApiError(409, "invalid_state", f"The alert is already in state {a.state.value}.")
    a.state = AlertState.acknowledged
    a.history.append(
        AlertHistoryEntry(at=ex.MISSION.sim_now, actor=user.display_name, role=user.role, action="acknowledged")
    )
    publish("alert.updated", ex.brief(a), a.crew_id)
    return a


@router.put(
    "/alerts/{alert_id}/plan/steps/{step_id}",
    response_model=Alert,
    summary="Tick a plan step",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def update_step(alert_id: str, step_id: str, body: StepUpdate, user: User = Depends(require_roles(*CREW))):
    """Ticks or unticks a step of the action plan.

    **SSE:** `alert.updated`."""
    a = _get(alert_id, user)
    step = next((s for s in a.plan_steps if s.id == step_id), None)
    if not step:
        raise ApiError(404, "not_found", f"Step {step_id} does not exist.")
    step.done, step.done_at = body.done, (ex.MISSION.sim_now if body.done else None)
    publish("alert.updated", ex.brief(a), a.crew_id)
    return a


@router.post(
    "/alerts/{alert_id}/escalate",
    response_model=Alert,
    summary="Escalate the alert",
    responses=E409,
    openapi_extra=roles(*CREW),
)
async def escalate(alert_id: str, body: EscalateRequest, user: User = Depends(require_roles(*CREW))):
    """Raises the alert by one level.

    * `to_level = 2` — the astronaut sends it to the crew medical officer. It shows up in `/cmo/queue`.
    * `to_level = 3` — **only the `cmo` role**. The backend automatically creates a signed and encrypted packet in
      the queue to Earth and puts its id in `packet_id`. There is no need to call `/link/outbox`.

    The level can never go down (409 `invalid_state`). Critical alerts can also be escalated automatically by the
    triage engine.

    **SSE:** `alert.updated`, and at level 3 also `packet.sent` when the window opens."""
    a = _get(alert_id, user)
    if body.to_level == 3 and user.role != Role.cmo:
        raise ApiError(403, "forbidden", "Only the crew medical officer can send an alert to Earth.")
    if body.to_level < a.level or (body.to_level == a.level and a.state == AlertState.escalated):
        raise ApiError(409, "invalid_state", f"The alert is already at level {a.level}.")
    a.level, a.state = body.to_level, AlertState.escalated
    if body.to_level == 3:
        a.packet_id = "pk-0007"
    a.history.append(
        AlertHistoryEntry(
            at=ex.MISSION.sim_now, actor=user.display_name, role=user.role, action="escalated", note=body.note
        )
    )
    publish("alert.updated", ex.brief(a), a.crew_id)
    return a


@router.post(
    "/alerts/{alert_id}/resolve",
    response_model=Alert,
    summary="Close the alert",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def resolve(alert_id: str, body: ResolveRequest, user: User = Depends(require_roles(*CREW))):
    """An astronaut can close level 1 alerts; level 2 and 3 alerts are closed by the crew medical officer.
    `outcome = monitoring` keeps the alert open and moves `recheck_at` by one more day.

    **SSE:** `alert.updated`."""
    a = _get(alert_id, user)
    if a.level >= 2 and user.role != Role.cmo:
        raise ApiError(403, "forbidden", "Level 2 and 3 alerts are closed by the crew medical officer.")
    if body.outcome != "monitoring":
        a.state = AlertState.resolved
    a.history.append(
        AlertHistoryEntry(
            at=ex.MISSION.sim_now, actor=user.display_name, role=user.role, action="resolved", note=body.note
        )
    )
    publish("alert.updated", ex.brief(a), a.crew_id)
    return a


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
):
    """Recommendations written by the team based on the NASA HRP risks, each with its source. The AI doctor only
    rephrases them."""
    return [
        r for r in ex.RECOMMENDATIONS if (topic is None or r.topic == topic) and (level is None or r.level == level)
    ]


@router.get(
    "/catalog/recommendations/{rec_id}",
    response_model=Recommendation,
    summary="One catalog recommendation",
    responses={k: ERRORS[k] for k in (401, 404)},
    openapi_extra=roles(*CREW, Role.earth),
)
async def get_recommendation(rec_id: str, user: User = Depends(current_user)):
    if rec_id not in ex.REC_BY_ID:
        raise ApiError(404, "not_found", f"Recommendation {rec_id} does not exist.")
    return ex.REC_BY_ID[rec_id]
