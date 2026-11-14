"""Autentificare și permisiuni — varianta MOCK.

Backend: înlocuiți `decode_token` cu verificarea reală a JWT-ului (HS256, secret din .env).
Restul (require_roles, crew_access) poate rămâne exact așa."""
import asyncio
import itertools
import json
from typing import Any

from fastapi import Depends, Header

from . import examples as ex
from .schemas import ErrorResponse, Role, User


class ApiError(Exception):
    """Ridicați asta oriunde; main.py o transformă în forma standard {error:{code,message,details}}."""

    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        self.status, self.code, self.message, self.details = status, code, message, details


#: răspunsurile de eroare comune, afișate în OpenAPI la fiecare endpoint protejat
ERRORS = {
    401: {"model": ErrorResponse, "description": "Lipsește tokenul sau e invalid (`unauthorized`)."},
    403: {"model": ErrorResponse, "description": "Rolul nu are voie (`forbidden`)."},
    404: {"model": ErrorResponse, "description": "Resursa nu există (`not_found`)."},
    409: {"model": ErrorResponse, "description": "Acțiunea nu e permisă în starea curentă (`invalid_state`)."},
    422: {"model": ErrorResponse, "description": "Date invalide (`validation_error`)."},
}


def roles(*allowed: Role) -> dict:
    """Metadate pentru OpenAPI/documentație: ce roluri pot apela endpoint-ul."""
    return {"x-roles": [r.value for r in allowed]}


ALL = (Role.astronaut, Role.cmo, Role.earth)
CREW = (Role.astronaut, Role.cmo)


def decode_token(token: str) -> User:
    # MOCK: tokenul este „mock-<username>”.
    # REAL: jwt.decode(token, SECRET, algorithms=["HS256"]) → claims {sub, role, crew_id, jti, exp};
    #       respinge dacă jti e pe lista de tokenuri revocate (logout); încarcă utilizatorul după sub.
    if token.startswith("mock-") and token[5:] in ex.USERS:
        return ex.USERS[token[5:]]
    raise ApiError(401, "unauthorized", "Token invalid sau expirat. Autentifică-te din nou.")


def current_user(authorization: str | None = Header(default=None)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "unauthorized", "Lipsește antetul Authorization: Bearer <token>.")
    return decode_token(authorization[7:].strip())


def require_roles(*allowed: Role):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in allowed:
            raise ApiError(403, "forbidden", "Rolul tău nu are acces la această resursă.", {"role": user.role.value})
        return user
    return dep


def crew_access(crew_id: str, user: User = Depends(require_roles(*CREW))) -> User:
    """Regula de proprietate a datelor:
    astronaut → doar propriul crew_id;  cmo → orice membru (accesul se scrie în jurnal);  earth → niciodată."""
    if crew_id not in ex.CREW_BY_ID:
        raise ApiError(404, "not_found", f"Nu există membrul de echipaj {crew_id}.")
    if user.role == Role.astronaut and user.crew_id != crew_id:
        raise ApiError(403, "forbidden", "Nu ai acces la datele altui membru al echipajului.")
    return user


# ------------------------------------------------------------------ difuzor SSE (în memorie)
_subscribers: set[asyncio.Queue] = set()
_ids = itertools.count(1)


def publish(type_: str, data: Any, crew_id: str | None = None) -> None:
    """Trimite un eveniment tuturor clienților conectați la /events."""
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    event = {"id": f"ev-{next(_ids):06d}", "type": type_, "at": ex.MISSION.sim_now.isoformat(),
             "crew_id": crew_id, "data": data}
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
