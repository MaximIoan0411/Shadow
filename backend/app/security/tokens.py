"""Tokenurile de acces (JWT, HS256). Fiecare token e legat de un singur cont și un singur `crew_id`."""
import base64
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .errors import InvalidToken

PROVIZORIU: tuple[str, ...] = ('issue', 'decode', 'revoke', 'is_revoked')
"""Funcțiile al căror corp e încă provizoriu. Echipa de securitate scoate numele pe măsură ce le termină."""

TTL_S = 12 * 3600


@dataclass(frozen=True)
class Claims:
    sub: str                 # id-ul contului, ex. "u-cm-2"
    role: str                # "astronaut" | "cmo" | "earth"
    crew_id: str | None   # None doar pentru "earth"
    jti: str                 # id unic al tokenului (pentru revocare)
    exp: int                 # secunde Unix


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# PROVIZORIU: HS256 scris cu hmac din biblioteca standard, ca să nu depindem încă de un pachet.
# Securitatea îl înlocuiește cu PyJWT (`jwt.encode` / `jwt.decode(..., algorithms=["HS256"])`).
def issue(*, user_id: str, role: str, crew_id: str | None, secret: str, ttl_s: int = TTL_S) -> tuple[str, Claims]:
    """Emite un token nou. Întoarce tokenul (text) și conținutul lui (pentru jurnal și pentru `expires_in`)."""
    claims = Claims(sub=user_id, role=role, crew_id=crew_id, jti=uuid.uuid4().hex, exp=int(time.time()) + ttl_s)
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64(json.dumps(claims.__dict__, separators=(",", ":")).encode())
    sig = _b64(hmac.new(secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest())
    return f"{header}.{body}.{sig}", claims


def decode(token: str, *, secret: str) -> Claims:
    """Verifică semnătura, algoritmul (doar HS256) și expirarea. Aruncă InvalidToken.
    NU verifică revocarea: aceea cere baza de date, vezi `is_revoked`."""
    try:
        header_b64, body_b64, sig_b64 = token.split(".")
        header: dict[str, Any] = json.loads(_unb64(header_b64))
        if header.get("alg") != "HS256":
            raise InvalidToken("algoritm nepermis")
        expected = hmac.new(secret.encode(), f"{header_b64}.{body_b64}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _unb64(sig_b64)):
            raise InvalidToken("semnătură invalidă")
        claims = Claims(**json.loads(_unb64(body_b64)))
    except InvalidToken:
        raise
    except Exception as e:  # noqa: BLE001
        raise InvalidToken("token malformat") from e
    if claims.exp < time.time():
        raise InvalidToken("token expirat")
    return claims


# PROVIZORIU: lista de revocări stă în memorie. Varianta reală scrie în tabelul `revoked_tokens` prin `session`.
_revoked: dict[str, datetime] = {}


async def revoke(session: Any, jti: str, expires_at: datetime) -> None:
    """Trece tokenul pe lista de revocări până la expirare (la `logout`). Se apelează în tranzacția cererii."""
    _revoked[jti] = expires_at


async def is_revoked(session: Any, jti: str) -> bool:
    """True dacă tokenul a fost revocat. Backend-ul o apelează după `decode`, la fiecare cerere."""
    exp = _revoked.get(jti)
    return exp is not None and exp > datetime.now(UTC)
