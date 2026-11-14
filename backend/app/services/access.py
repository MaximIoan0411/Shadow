import logging
from typing import Literal

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clock import clock
from ..db import session as db
from ..db.models.security import AccessLog
from ..schemas import AccessLogEntry, Role, User
from ..security import access_log

log = logging.getLogger(__name__)

API_PREFIX = "/api/v1/"
ROLES = {r.value for r in Role}


def resource_for(path: str) -> str:
    return path.removeprefix(API_PREFIX).strip("/")


def read_action_for(path: str) -> str:
    resource = resource_for(path)
    if resource.endswith("/dashboard"):
        return "read_dashboard"
    if "/pillars" in resource:
        return "read_pillar"
    if "/alerts" in resource or resource.startswith("alerts/"):
        return "read_alert"
    return "read_crew_data"


async def record(
    session: AsyncSession,
    user: User,
    *,
    action: str,
    resource: str,
    crew_id: str | None,
    outcome: Literal["allowed", "denied"],
) -> None:
    await access_log.write(
        session,
        at=clock.now(),
        actor=user.display_name,
        actor_role=user.role.value,
        action=action,
        resource=resource,
        crew_id=crew_id,
        outcome=outcome,
    )


async def record_denied(request: Request) -> None:
    user: User | None = getattr(request.state, "user", None)
    if user is None or db.SessionLocal is None:
        return
    crew_id = request.path_params.get("crew_id")
    try:
        async with db.SessionLocal() as s:
            await record(
                s,
                user,
                action="access_denied",
                resource=resource_for(request.url.path),
                crew_id=crew_id,
                outcome="denied",
            )
            await s.commit()
    except Exception:
        log.exception("could not write access_denied to the access log")


async def entries(session: AsyncSession, user: User, crew_id: str | None, limit: int) -> list[AccessLogEntry]:
    target = user.crew_id if user.role == Role.astronaut else crew_id
    stmt = select(AccessLog).where(AccessLog.actor_role.in_(ROLES)).order_by(AccessLog.id.desc()).limit(limit)
    if target is not None:
        stmt = stmt.where(AccessLog.crew_id == target)
    return [
        AccessLogEntry(
            id=e.id,
            at=e.at,
            actor=e.actor,
            actor_role=Role(e.actor_role),
            action=e.action,
            resource=e.resource,
            crew_id=e.crew_id,
            outcome=e.outcome,
            prev_hash=e.prev_hash,
            hash=e.hash,
        )
        for e in (await session.scalars(stmt)).all()
    ]
