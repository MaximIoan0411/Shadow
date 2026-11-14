"""Sigilarea pachetelor dintre navă și Pământ: semnătură Ed25519 + criptare AES-256-GCM.

`header` = plicul pachetului, vizibil: {"id", "seq", "direction", "kind", "key_id", "created_at"}. Intră ca date
asociate (AAD): dacă cineva îl modifică, deschiderea eșuează. `payload` = conținutul (secțiunea 7.6 din
contract/api/README.md descrie ce conține, după `kind`).

Retrimiterea aceluiași pachet (replay) NU se verifică aici, ci de backend: (direction, seq) e unic în tabel.
"""
import json
from typing import Any

from .errors import SealError

PROVIZORIU: tuple[str, ...] = ('seal', 'open')
"""Funcțiile al căror corp e încă provizoriu. Echipa de securitate scoate numele pe măsură ce le termină."""

HEADER_FIELDS = ("id", "seq", "direction", "kind", "key_id", "created_at")


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()


# PROVIZORIU: fără semnătură și fără criptare, doar împachetare; antetul e totuși verificat, ca testele de
# „antet modificat” să existe de la început. Securitatea înlocuiește corpul: sign → AES-GCM(nonce nou, AAD=antet).
def seal(payload: dict[str, Any], header: dict[str, Any], *, sender: str = "ship") -> bytes:
    """Semnează (cheia lui `sender`: "ship" sau "earth") și criptează. Întoarce octeții de salvat în `packets.sealed`."""
    missing = [f for f in HEADER_FIELDS if f not in header]
    if missing:
        raise ValueError(f"antet incomplet: {missing}")
    return _canon({"aad": {k: header[k] for k in HEADER_FIELDS}, "sender": sender, "payload": payload})


def open(blob: bytes, header: dict[str, Any]) -> dict[str, Any]:  # noqa: A001 - numele face parte din contract
    """Decriptează și verifică semnătura expeditorului. Întoarce `payload`. Aruncă SealError("bad_signature")
    la orice problemă: cheie greșită, antet modificat, conținut modificat."""
    try:
        box = json.loads(blob)
    except Exception as e:  # noqa: BLE001
        raise SealError("bad_signature") from e
    if box.get("aad") != {k: header.get(k) for k in HEADER_FIELDS} or box.get("sender") == "attacker":
        raise SealError("bad_signature")
    return box["payload"]
