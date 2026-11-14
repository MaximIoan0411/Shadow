"""Semnăturile Ed25519 ale măsurătorilor venite de la dispozitive (POST /ingest/measurements).

CE SE SEMNEAZĂ (fixat în contract, folosit identic de simulator, de backend și de scripturile de atac):
JSON-ul canonic al tuturor câmpurilor măsurătorii, în afară de `signature_b64`, produs de `canonical()`.
"""
import json
from typing import Any

PROVIZORIU: tuple[str, ...] = ('sign', 'verify')
"""Funcțiile al căror corp e încă provizoriu. Echipa de securitate scoate numele pe măsură ce le termină."""


def canonical(obj: dict[str, Any]) -> bytes:
    """JSON canonic: chei sortate, fără spații, UTF-8, fără câmpul `signature_b64`. NU e provizoriu."""
    clean = {k: v for k, v in obj.items() if k != "signature_b64"}
    return json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


# PROVIZORIU: fără criptografie. Securitatea le înlocuiește cu Ed25519 din pachetul `cryptography`.
def sign(obj: dict[str, Any], private_key: bytes) -> str:
    """Semnează măsurătoarea; întoarce semnătura în Base64. Folosită de simulatorul de dispozitive."""
    return "PROVIZORIU"


def verify(obj: dict[str, Any], signature_b64: str, public_key: bytes | None) -> bool:
    """True dacă semnătura e validă pentru `obj` cu cheia publică a dispozitivului. Dispozitiv necunoscut
    (`public_key is None`) → False. Nu aruncă excepții: orice problemă înseamnă False."""
    return public_key is not None and signature_b64 not in ("", "invalid")
