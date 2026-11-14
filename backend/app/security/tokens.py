"""Tokenurile de acces (JWT, HS256). Fiecare token e legat de un singur cont și un singur `crew_id`."""
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import jwt
from sqlalchemy import delete

from ..db.models.users import RevokedToken
from .errors import InvalidToken

PROVIZORIU: tuple[str, ...] = ()
"""Funcțiile al căror corp e încă provizoriu. Echipa de securitate scoate numele pe măsură ce le termină."""

TTL_S = 12 * 3600
ALGORITHM = "HS256"
REQUIRED_CLAIMS = ("exp", "sub", "role", "jti")


@dataclass(frozen=True)
class Claims:
    sub: str                 # id-ul contului, ex. "u-cm-2"
    role: str                # "astronaut" | "cmo" | "earth"
    crew_id: str | None   # None doar pentru "earth"
    jti: str                 # id unic al tokenului (pentru revocare)
    exp: int                 # secunde Unix


def issue(*, user_id: str, role: str, crew_id: str | None, secret: str, ttl_s: int = TTL_S) -> tuple[str, Claims]:
    """Emite un token nou. Întoarce tokenul (text) și conținutul lui (pentru jurnal și pentru `expires_in`)."""
    now = int(time.time())
    claims = Claims(sub=user_id, role=role, crew_id=crew_id, jti=uuid.uuid4().hex, exp=now + ttl_s)
    return jwt.encode({**asdict(claims), "iat": now}, secret, algorithm=ALGORITHM), claims


def decode(token: str, *, secret: str) -> Claims:
    """Verifică semnătura, algoritmul (doar HS256) și expirarea. Aruncă InvalidToken.
    NU verifică revocarea: aceea cere baza de date, vezi `is_revoked`."""
    try:
        data = jwt.decode(token, secret, algorithms=[ALGORITHM], options={"require": list(REQUIRED_CLAIMS)})
    except jwt.PyJWTError as e:
        raise InvalidToken(str(e)) from e
    crew_id = data.get("crew_id")
    if not all(isinstance(data[name], str) and data[name] for name in ("sub", "role", "jti")):
        raise InvalidToken("token malformat")
    if crew_id is not None and not isinstance(crew_id, str):
        raise InvalidToken("token malformat")
    return Claims(sub=data["sub"], role=data["role"], crew_id=crew_id, jti=data["jti"], exp=int(data["exp"]))


async def revoke(session: Any, jti: str, expires_at: datetime) -> None:
    """Trece tokenul pe lista de revocări până la expirare (la `logout`). Se apelează în tranzacția cererii."""
    # tokenurile expirate nu mai trec oricum de `decode`: rândurile lor se șterg, ca tabelul să rămână mic
    await session.execute(delete(RevokedToken).where(RevokedToken.expires_at < datetime.now(UTC)))
    if await session.get(RevokedToken, jti) is None:
        session.add(RevokedToken(jti=jti, expires_at=expires_at))
    await session.flush()


async def is_revoked(session: Any, jti: str) -> bool:
    """True dacă tokenul a fost revocat. Backend-ul o apelează după `decode`, la fiecare cerere."""
    row = await session.get(RevokedToken, jti)
    return row is not None and row.expires_at > datetime.now(UTC)
