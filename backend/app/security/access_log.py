"""Jurnalul de acces: doar se adaugă; fiecare intrare conține hash-ul celei dinainte.

hash = SHA-256( prev_hash + JSON canonic al intrării fără câmpurile `hash` și `prev_hash` ), în hex, primele 16 caractere
afișate. Prima intrare are prev_hash = "0" * 16.

Acțiuni: login, login_failed, logout, read_dashboard, read_pillar, read_alert, escalate, read_packet,
access_denied, reset.
"""
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Literal

PROVIZORIU: tuple[str, ...] = ('write', 'verify_chain')
"""Funcțiile al căror corp e încă provizoriu. Echipa de securitate scoate numele pe măsură ce le termină."""

GENESIS = "0" * 16


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


# PROVIZORIU: jurnalul stă în memorie. Varianta reală face INSERT în tabelul `access_log` prin `session`,
# în aceeași tranzacție cu cererea, și citește ultimul hash din tabel.
_entries: list[Entry] = []


async def write(session: Any, *, at: datetime, actor: str, actor_role: str, action: str, resource: str,
                crew_id: str | None, outcome: Literal["allowed", "denied"]) -> Entry:
    """Adaugă o intrare. Se apelează în tranzacția cererii; nu face commit."""
    prev = _entries[-1].hash if _entries else GENESIS
    fields = dict(id=len(_entries) + 1, at=at, actor=actor, actor_role=actor_role, action=action,
                  resource=resource, crew_id=crew_id, outcome=outcome)
    e = Entry(**fields, prev_hash=prev, hash=entry_hash(prev, fields))
    _entries.append(e)
    return e


async def verify_chain(session: Any) -> bool:
    """True dacă niciun rând nu a fost modificat sau șters (lanțul de hash-uri e întreg)."""
    prev = GENESIS
    for e in _entries:
        fields = {k: v for k, v in asdict(e).items() if k not in ("prev_hash", "hash")}
        if e.prev_hash != prev or e.hash != entry_hash(prev, fields):
            return False
        prev = e.hash
    return True
