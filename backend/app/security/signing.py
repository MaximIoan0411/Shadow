"""Semnăturile Ed25519 ale măsurătorilor venite de la dispozitive (POST /ingest/measurements).

CE SE SEMNEAZĂ (fixat în contract, folosit identic de simulator, de backend și de scripturile de atac):
JSON-ul canonic al tuturor câmpurilor măsurătorii, în afară de `signature_b64`, produs de `canonical()`.

Backend-ul verifică semnătura peste obiectul JSON EXACT cum a sosit, nu peste modelul validat: după validare `61`
devine `61.0`, iar ora își schimbă scrierea, deci forma canonică n-ar mai fi cea semnată de dispozitiv.
"""
import base64
import json
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

PROVIZORIU: tuple[str, ...] = ()
"""Funcțiile al căror corp e încă provizoriu. Echipa de securitate scoate numele pe măsură ce le termină."""


def canonical(obj: dict[str, Any]) -> bytes:
    """JSON canonic: chei sortate, fără spații, UTF-8, fără câmpul `signature_b64`. NU e provizoriu."""
    clean = {k: v for k, v in obj.items() if k != "signature_b64"}
    return json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def sign(obj: dict[str, Any], private_key: bytes) -> str:
    """Semnează măsurătoarea; întoarce semnătura în Base64. Folosită de simulatorul de dispozitive."""
    key = Ed25519PrivateKey.from_private_bytes(private_key)
    return base64.b64encode(key.sign(canonical(obj))).decode()


def verify(obj: dict[str, Any], signature_b64: str, public_key: bytes | None) -> bool:
    """True dacă semnătura e validă pentru `obj` cu cheia publică a dispozitivului. Dispozitiv necunoscut
    (`public_key is None`) → False. Nu aruncă excepții: orice problemă înseamnă False."""
    if public_key is None:
        return False
    try:
        signature = base64.b64decode(signature_b64, validate=True)
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, canonical(obj))
    except Exception:  # noqa: BLE001 - semnătură greșită, Base64 stricat, cheie stricată: toate înseamnă „nu”
        return False
    return True
