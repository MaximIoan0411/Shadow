"""Blocarea contului după prea multe parole greșite. Blocarea e PE CONT: nu-i afectează pe ceilalți astronauți.

Regula: 5 parole greșite în 5 minute reale → cont blocat 60 de secunde reale. Starea stă în memorie (se pierde la
repornire, ceea ce e acceptabil pentru prototip). Timpul e cel REAL, nu cel al misiunii.
"""
import time

from .errors import AccountLocked

PROVIZORIU: tuple[str, ...] = ()
"""Funcțiile al căror corp e încă provizoriu. Echipa de securitate scoate numele pe măsură ce le termină."""

MAX_ATTEMPTS = 5
WINDOW_S = 300
LOCK_S = 60
MAX_TRACKED = 10_000
"""Câte nume ținem minte cel mult: numele inventate la autentificare nu pot umple memoria."""

_failed: dict[str, list[float]] = {}
_locked_until: dict[str, float] = {}


def check(username: str) -> None:
    """Aruncă AccountLocked dacă acest cont e blocat. Se apelează ÎNAINTE de verificarea parolei."""
    until = _locked_until.get(username, 0.0)
    now = time.time()
    if until > now:
        raise AccountLocked(int(until - now) + 1)


def record_failure(username: str) -> None:
    """O parolă greșită. La a 5-a în fereastra de 5 minute, contul se blochează."""
    now = time.time()
    tries = [t for t in _failed.get(username, []) if now - t < WINDOW_S] + [now]
    if len(tries) >= MAX_ATTEMPTS:
        _locked_until[username] = now + LOCK_S
        _failed.pop(username, None)
    else:
        _failed[username] = tries
    if len(_failed) + len(_locked_until) > MAX_TRACKED:
        _forget_old(now)


def _forget_old(now: float) -> None:
    """Uită încercările și blocările expirate; dacă tot sunt prea multe, cele mai vechi încercări (niciodată o blocare)."""
    for name in [name for name, tries in _failed.items() if now - tries[-1] >= WINDOW_S]:
        del _failed[name]
    for name in [name for name, until in _locked_until.items() if until <= now]:
        del _locked_until[name]
    while _failed and len(_failed) + len(_locked_until) > MAX_TRACKED:
        del _failed[next(iter(_failed))]


def clear(username: str) -> None:
    """Autentificare reușită: șterge încercările greșite ale contului."""
    _failed.pop(username, None)


def reset_all() -> None:
    """Pentru `POST /sim/reset`: șterge toate blocările."""
    _failed.clear()
    _locked_until.clear()
