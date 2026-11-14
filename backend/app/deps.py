import asyncio
import itertools
import json
from typing import Any

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .clock import clock
from .config import Settings
from .datafiles import DataBundle
from .db.session import get_session
from .schemas import ErrorResponse, Role, User


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        self.status, self.code, self.message, self.details = status, code, message, details


ERRORS = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token (`unauthorized`)."},
    403: {"model": ErrorResponse, "description": "This role is not allowed (`forbidden`)."},
    404: {"model": ErrorResponse, "description": "The resource does not exist (`not_found`)."},
    409: {"model": ErrorResponse, "description": "The action is not allowed in the current state (`invalid_state`)."},
    422: {"model": ErrorResponse, "description": "Invalid data (`validation_error`)."},
}


def roles(*allowed: Role) -> dict:
    return {"x-roles": [r.value for r in allowed]}


ALL = (Role.astronaut, Role.cmo, Role.earth)
CREW = (Role.astronaut, Role.cmo)


def get_data(request: Request) -> DataBundle:
    return request.app.state.data


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


async def current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    from .services import auth as auth_service

    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "unauthorized", "Missing header Authorization: Bearer <token>.")
    token = authorization[7:].strip()
    settings = request.app.state.settings
    user = await auth_service.user_from_token(
        session, token, secret=settings.jwt_secret, allow_mock=settings.allow_mock_tokens
    )
    request.state.token = token
    request.state.user = user
    return user


def require_roles(*allowed: Role):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in allowed:
            raise ApiError(
                403, "forbidden", "Your role does not have access to this resource.", {"role": user.role.value}
            )
        return user

    return dep


async def crew_access(
    crew_id: str,
    request: Request,
    user: User = Depends(require_roles(*CREW)),
    session: AsyncSession = Depends(get_session),
) -> User:
    from .db.models.users import Crew
    from .services import access

    if await session.get(Crew, crew_id) is None:
        raise ApiError(404, "not_found", f"Crew member {crew_id} does not exist.")
    if user.role == Role.astronaut and user.crew_id != crew_id:
        raise ApiError(403, "forbidden", "You do not have access to another crew member's data.")
    if user.role == Role.cmo and user.crew_id != crew_id:
        path = request.url.path
        await access.record(
            session,
            user,
            action=access.read_action_for(path),
            resource=access.resource_for(path),
            crew_id=crew_id,
            outcome="allowed",
        )
        await session.commit()
    return user


_subscribers: set[asyncio.Queue] = set()
_ids = itertools.count(1)


EARTH_EVENT_PREFIXES = ("packet.", "mission.", "environment.")
ALERT_EVENT_PREFIX = "alert."
CMO_MIN_LEVEL = 2
EARTH_LEVEL = 3
ONLY_CMO_SENDS_ALERTS = "Only the crew medical officer can send an alert to Earth."
SUBSCRIBER_QUEUE_MAX = 1000


def publish(type_: str, data: Any, crew_id: str | None = None) -> None:
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    event = {
        "id": f"ev-{next(_ids):06d}",
        "type": type_,
        "at": clock.now().isoformat(),
        "crew_id": crew_id,
        "data": data,
    }
    for q in list(_subscribers):
        if q.full():  # a client that stopped reading: drop its oldest event instead of growing without limit
            q.get_nowait()
        q.put_nowait(event)


def visible_to(user: User, event: dict) -> bool:
    """An astronaut gets only their own and the general events; earth only mission.*, environment.* and packet.*;
    the crew medical officer gets everything."""
    if user.role == Role.astronaut:
        return event.get("crew_id") in (None, user.crew_id)
    if user.role == Role.earth:
        return event["type"].startswith(EARTH_EVENT_PREFIXES)
    if event["type"].startswith(ALERT_EVENT_PREFIX) and event.get("crew_id") != user.crew_id:
        # same rule as GET /alerts/{id}: the crew medical officer sees a colleague's alert from level 2 up
        data = event.get("data")
        level = data.get("level") if isinstance(data, dict) else None
        return isinstance(level, int) and level >= CMO_MIN_LEVEL
    return True


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=SUBSCRIBER_QUEUE_MAX)
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    _subscribers.discard(q)


def sse_format(event: dict) -> str:
    return f"id: {event['id']}\nevent: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
