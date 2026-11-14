"""Jurnalul de acces: doar se adaugă; fiecare intrare conține hash-ul celei dinainte.

hash = SHA-256( prev_hash + JSON canonic al intrării fără câmpurile `hash` și `prev_hash` ), în hex, primele 16 caractere
afișate. Prima intrare are prev_hash = "0" * 16.

Acțiuni: login, login_failed, logout, read_dashboard, read_pillar, read_alert, escalate, read_packet,
access_denied, reset.

Jurnalul stă în tabelul `access_log` și NU se șterge la `POST /sim/reset`. Lanțul arată o intrare modificată sau
ștearsă din mijloc; ștergerea ultimelor intrări se vede doar dacă ultimul hash e păstrat și în altă parte.
"""
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import select

from ..db.models.security import AccessLog

PROVIZORIU: tuple[str, ...] = ()
"""Funcțiile al căror corp e încă provizoriu. Echipa de securitate scoate numele pe măsură ce le termină."""

GENESIS = "0" * 16
FIELDS = ("id", "at", "actor", "actor_role", "action", "resource", "crew_id", "outcome")


@dataclass(frozen=True)
class Entry:
    id: int
    at: datetime                       # timpul misiunii (clock.now())
    actor: str                         # display_name al contului, sau "SHADOW" / "necunoscut"
    actor_role: str
    action: str
    resource: str                      # ex. "alerts/al-1042", "crew/cm-2/dashboard"
    crew_id: str | None
    outcome: Literal["allowed", "denied"]
    prev_hash: str
    hash: str


def entry_hash(prev_hash: str, fields: dict[str, Any]) -> str:
    """NU e provizoriu: formula lanțului, folosită și de `verify_chain`."""
    body = json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256((prev_hash + body).encode()).hexdigest()[:16]


def _fields(row: AccessLog) -> dict[str, Any]:
    return {name: getattr(row, name) for name in FIELDS}


async def write(session: Any, *, at: datetime, actor: str, actor_role: str, action: str, resource: str,
                crew_id: str | None, outcome: Literal["allowed", "denied"]) -> Entry:
    """Adaugă o intrare. Se apelează în tranzacția cererii; nu face commit."""
    # Întâi INSERT: de aici tranzacția ține singură dreptul de scriere în SQLite, deci nicio altă cerere nu poate
    # adăuga între citirea hash-ului anterior și salvarea celui nou. Abia apoi se leagă intrarea de cea dinainte.
    row = AccessLog(at=at, actor=actor, actor_role=actor_role, action=action, resource=resource,
                    crew_id=crew_id, outcome=outcome, prev_hash="", hash="")
    session.add(row)
    await session.flush()
    await session.refresh(row)   # valorile exact cum le-a păstrat baza de date: din ele se recalculează lanțul
    previous = await session.scalar(
        select(AccessLog.hash).where(AccessLog.id < row.id).order_by(AccessLog.id.desc()).limit(1)
    )
    row.prev_hash = previous or GENESIS
    row.hash = entry_hash(row.prev_hash, _fields(row))
    await session.flush()
    return Entry(**_fields(row), prev_hash=row.prev_hash, hash=row.hash)


async def verify_chain(session: Any) -> bool:
    """True dacă niciun rând nu a fost modificat sau șters (lanțul de hash-uri e întreg)."""
    prev = GENESIS
    for row in (await session.scalars(select(AccessLog).order_by(AccessLog.id))).all():
        if row.prev_hash != prev or row.hash != entry_hash(prev, _fields(row)):
            return False
        prev = row.hash
    return True
