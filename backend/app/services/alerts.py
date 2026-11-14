from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..clock import clock
from ..datafiles import DataBundle
from ..db.models.alerts import Alert as AlertRow
from ..db.models.alerts import AlertHistory
from ..deps import EARTH_LEVEL, ONLY_CMO_SENDS_ALERTS, ApiError
from ..schemas import (
    Alert,
    AlertBrief,
    AlertHistoryEntry,
    AlertState,
    AlertTopic,
    Evidence,
    PlanStep,
    Recommendation,
    Role,
    User,
)
from .events import Event

_REC_FIELDS = set(Recommendation.model_fields)


def recommendation(data: DataBundle, rec_id: str) -> Recommendation:
    entry = data.catalog.by_id().get(rec_id)
    if entry is None:
        raise ApiError(404, "not_found", f"Recommendation {rec_id} does not exist.")
    return Recommendation(**entry.model_dump(include=_REC_FIELDS))


def recommendations(data: DataBundle, topic: AlertTopic | None, level: int | None) -> list[Recommendation]:
    return [
        Recommendation(**r.model_dump(include=_REC_FIELDS))
        for r in data.catalog.recommendations
        if (topic is None or r.topic == topic) and (level is None or r.level == level)
    ]


def brief(a: AlertRow) -> AlertBrief:
    return AlertBrief(
        id=a.id,
        crew_id=a.crew_id,
        topic=a.topic,
        level=a.level,
        status=a.status,
        state=a.state,
        title=a.title,
        created_at=a.created_at,
    )


def to_schema(a: AlertRow, data: DataBundle) -> Alert:
    return Alert(
        **brief(a).model_dump(),
        explanation=a.explanation,
        cause=a.cause,
        cause_explanation=a.cause_explanation,
        evidence=[Evidence(**e) for e in a.evidence],
        recommendation=recommendation(data, a.recommendation_id),
        plan_steps=[PlanStep(id=s.step_id, text=s.text, done=s.done, done_at=s.done_at) for s in a.steps],
        recheck_at=a.recheck_at,
        packet_id=a.packet_id,
        earth_reply=a.earth_reply,
        history=[
            AlertHistoryEntry(
                at=h.at, actor=h.actor, role=Role(h.role) if h.role else None, action=h.action, note=h.note
            )
            for h in a.history
        ],
    )


def _with_children():
    return (selectinload(AlertRow.steps), selectinload(AlertRow.history))


def _sorted(rows) -> list[AlertRow]:
    return sorted(rows, key=lambda a: (-a.level, -a.created_at.timestamp()))


async def get_row(session: AsyncSession, alert_id: str, user: User) -> AlertRow:
    a = await session.scalar(select(AlertRow).where(AlertRow.id == alert_id).options(*_with_children()))
    if a is None:
        raise ApiError(404, "not_found", f"Alert {alert_id} does not exist.")
    if user.role == Role.astronaut and a.crew_id != user.crew_id:
        raise ApiError(403, "forbidden", "You do not have access to another crew member's alert.")
    if user.role == Role.cmo and a.level < 2 and a.crew_id != user.crew_id:
        raise ApiError(403, "forbidden", "The crew medical officer only sees level 2 and 3 alerts.")
    return a


async def list_for_crew(
    session: AsyncSession, crew_id: str, user: User, state: AlertState | None, topic: AlertTopic | None
) -> list[AlertBrief]:
    stmt = select(AlertRow).where(AlertRow.crew_id == crew_id)
    stmt = stmt.where(AlertRow.state == state.value) if state else stmt.where(AlertRow.state != "resolved")
    if topic:
        stmt = stmt.where(AlertRow.topic == topic.value)
    if user.role == Role.cmo and user.crew_id != crew_id:
        stmt = stmt.where(AlertRow.level >= 2)
    return [brief(a) for a in _sorted((await session.scalars(stmt)).all())]


async def cmo_queue(session: AsyncSession) -> list[AlertBrief]:
    stmt = select(AlertRow).where(AlertRow.level >= 2, AlertRow.state != "resolved")
    return [brief(a) for a in _sorted((await session.scalars(stmt)).all())]


def _history(a: AlertRow, user: User, action: str, note: str | None = None) -> None:
    now = clock.now()
    a.history.append(AlertHistory(at=now, actor=user.display_name, role=user.role.value, action=action, note=note))
    a.updated_at = now


async def _save(session: AsyncSession, a: AlertRow, data: DataBundle) -> tuple[Alert, list[Event]]:
    await session.commit()
    return to_schema(a, data), [Event("alert.updated", brief(a).model_dump(mode="json"), a.crew_id)]


async def acknowledge(session: AsyncSession, data: DataBundle, alert_id: str, user: User) -> tuple[Alert, list[Event]]:
    a = await get_row(session, alert_id, user)
    if a.state != AlertState.active.value:
        raise ApiError(409, "invalid_state", f"The alert is already in state {a.state}.")
    a.state = AlertState.acknowledged.value
    _history(a, user, "acknowledged")
    return await _save(session, a, data)


async def update_step(
    session: AsyncSession, data: DataBundle, alert_id: str, step_id: str, done: bool, user: User
) -> tuple[Alert, list[Event]]:
    a = await get_row(session, alert_id, user)
    step = next((s for s in a.steps if s.step_id == step_id), None)
    if step is None:
        raise ApiError(404, "not_found", f"Step {step_id} does not exist.")
    step.done = done
    step.done_at = clock.now() if done else None
    if done:
        _history(a, user, "step_done", step.text)
    else:
        a.updated_at = clock.now()
    return await _save(session, a, data)


async def escalate(
    session: AsyncSession, data: DataBundle, alert_id: str, to_level: int, note: str | None, user: User
) -> tuple[Alert, list[Event]]:
    a = await get_row(session, alert_id, user)
    if to_level == EARTH_LEVEL and user.role != Role.cmo:
        raise ApiError(403, "forbidden", ONLY_CMO_SENDS_ALERTS)
    if a.state == AlertState.resolved.value:
        raise ApiError(409, "invalid_state", "The alert is already resolved.")
    if to_level < a.level or (to_level == a.level and a.state == AlertState.escalated.value):
        raise ApiError(409, "invalid_state", f"The alert is already at level {a.level}.")
    a.level = to_level
    a.status = "alert"
    a.state = AlertState.escalated.value
    _history(a, user, "escalated", note)
    if to_level == EARTH_LEVEL:
        from . import link as link_service

        await link_service.send_alert_to_earth(session, data, a, sender=user.display_name, note=note)
    return await _save(session, a, data)


async def resolve(
    session: AsyncSession, data: DataBundle, alert_id: str, outcome: str, note: str | None, user: User
) -> tuple[Alert, list[Event]]:
    a = await get_row(session, alert_id, user)
    if a.level >= 2 and user.role != Role.cmo:
        raise ApiError(403, "forbidden", "Level 2 and 3 alerts are closed by the crew medical officer.")
    if a.state == AlertState.resolved.value:
        raise ApiError(409, "invalid_state", "The alert is already resolved.")
    if outcome == "monitoring":
        a.recheck_at = (a.recheck_at or clock.now()) + timedelta(days=1)
        _history(a, user, "rechecked", note)
    else:
        a.state = AlertState.resolved.value
        _history(a, user, "resolved", note or ("False alarm." if outcome == "false_alarm" else None))
    return await _save(session, a, data)


RECHECK_STEP_S = 5.0


async def recheck_loop(data: DataBundle) -> None:
    """Background task, every 5 real seconds, with its own session: the alerts whose recheck time has come
    (services/pipeline.recheck_due). Events after commit; an error is logged and the loop goes on."""
    import asyncio
    import logging

    from ..db import session as db
    from . import pipeline
    from .events import publish_all

    log = logging.getLogger(__name__)
    while True:
        try:
            async with db.SessionLocal() as s:
                events = await pipeline.recheck_due(s, data)
                await s.commit()
            publish_all(events)
        except Exception:
            log.exception("recheck loop failed; continuing")
        await asyncio.sleep(RECHECK_STEP_S)
