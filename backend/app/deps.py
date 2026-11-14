import asyncio
import itertools
import json
from typing import Any

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from . import examples as ex
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
    return user


def require_roles(*allowed: Role):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in allowed:
            raise ApiError(
                403, "forbidden", "Your role does not have access to this resource.", {"role": user.role.value}
            )
        return user

    return dep


def crew_access(crew_id: str, user: User = Depends(require_roles(*CREW))) -> User:
    if crew_id not in ex.CREW_BY_ID:
        raise ApiError(404, "not_found", f"Crew member {crew_id} does not exist.")
    if user.role == Role.astronaut and user.crew_id != crew_id:
        raise ApiError(403, "forbidden", "You do not have access to another crew member's data.")
    return user


_subscribers: set[asyncio.Queue] = set()
_ids = itertools.count(1)


def publish(type_: str, data: Any, crew_id: str | None = None) -> None:
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    event = {
        "id": f"ev-{next(_ids):06d}",
        "type": type_,
        "at": ex.MISSION.sim_now.isoformat(),
        "crew_id": crew_id,
        "data": data,
    }
    for q in list(_subscribers):
        q.put_nowait(event)


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    _subscribers.discard(q)


def sse_format(event: dict) -> str:
    return f"id: {event['id']}\nevent: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
