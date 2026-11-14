"""Sigilarea pachetelor dintre navă și Pământ: semnătură Ed25519 + criptare AES-256-GCM.

`header` = plicul pachetului, vizibil: {"id", "seq", "direction", "kind", "key_id", "created_at"}. Intră ca date
asociate (AAD): dacă cineva îl modifică, deschiderea eșuează. `payload` = conținutul (secțiunea 7.6 din
contract/api/README.md descrie ce conține, după `kind`).

Cum e făcut un pachet sigilat (JSON, cu câmpurile în Base64):
    ciphertext = AES-256-GCM(cheia legăturii, nonce nou de 12 octeți, payload canonic, AAD = antetul canonic)
    signature  = Ed25519(cheia expeditorului, "shadow-packet-v1" + antet canonic + nonce + ciphertext)
Semnătura se verifică ÎNAINTE de decriptare, cu cheia publică a celui care are voie să trimită în acea direcție
(`down` = nava, `up` = Pământul). Cine are doar cheia legăturii nu poate fabrica un pachet: îi lipsește cheia
de semnare. Cine schimbă antetul, nonce-ul sau conținutul strică semnătura.

Retrimiterea aceluiași pachet (replay) NU se verifică aici, ci de backend: (direction, seq) e unic în tabel.
"""
import base64
import json
import os
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .errors import SealError
from .keys import Keys

PROVIZORIU: tuple[str, ...] = ()
"""Funcțiile al căror corp e încă provizoriu. Echipa de securitate scoate numele pe măsură ce le termină."""

HEADER_FIELDS = ("id", "seq", "direction", "kind", "key_id", "created_at")
DOMAIN = b"shadow-packet-v1"
NONCE_BYTES = 12
SENDER_OF_DIRECTION = {"down": "ship", "up": "earth"}
ATTACKER = "attacker"
"""Doar pentru demo și scripturile de atac: semnează cu o cheie aruncată, deci pachetul NU trece de `open`."""

_keys: Keys | None = None


def configure(keys: Keys) -> None:
    """Apelată o dată, la pornire (din lifespan), cu cheile încărcate de `keys.load_keys`."""
    global _keys
    _keys = keys


def _require_keys() -> Keys:
    if _keys is None:
        raise RuntimeError("sealing not configured: call sealing.configure(keys) at startup")
    return _keys


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()


def _aad(header: dict[str, Any]) -> bytes:
    return _canon({k: header[k] for k in HEADER_FIELDS})


def _signing_key(sender: str) -> Ed25519PrivateKey:
    keys = _require_keys()
    if sender == ATTACKER:
        return Ed25519PrivateKey.generate()
    private = {"ship": keys.ship_private, "earth": keys.earth_private}.get(sender)
    if private is None:
        raise ValueError(f"unknown sender: {sender!r}")
    return Ed25519PrivateKey.from_private_bytes(private)


def seal(payload: dict[str, Any], header: dict[str, Any], *, sender: str = "ship") -> bytes:
    """Semnează (cheia lui `sender`: "ship" sau "earth") și criptează. Întoarce octeții de salvat în `packets.sealed`."""
    missing = [f for f in HEADER_FIELDS if f not in header]
    if missing:
        raise ValueError(f"antet incomplet: {missing}")
    aad = _aad(header)
    nonce = os.urandom(NONCE_BYTES)
    ciphertext = AESGCM(_require_keys().link_aes_key).encrypt(nonce, _canon(payload), aad)
    signature = _signing_key(sender).sign(DOMAIN + aad + nonce + ciphertext)
    return _canon(
        {
            "v": 1,
            "nonce_b64": base64.b64encode(nonce).decode(),
            "ciphertext_b64": base64.b64encode(ciphertext).decode(),
            "signature_b64": base64.b64encode(signature).decode(),
        }
    )


def open(blob: bytes, header: dict[str, Any]) -> dict[str, Any]:  # noqa: A001 - numele face parte din contract
    """Decriptează și verifică semnătura expeditorului. Întoarce `payload`. Aruncă SealError("bad_signature")
    la orice problemă: cheie greșită, antet modificat, conținut modificat."""
    keys = _require_keys()
    try:
        box = json.loads(blob)
        nonce = base64.b64decode(box["nonce_b64"], validate=True)
        ciphertext = base64.b64decode(box["ciphertext_b64"], validate=True)
        signature = base64.b64decode(box["signature_b64"], validate=True)
        aad = _aad(header)
        sender = SENDER_OF_DIRECTION[header["direction"]]
        private = keys.ship_private if sender == "ship" else keys.earth_private
        public = Ed25519PrivateKey.from_private_bytes(private).public_key()
        public.verify(signature, DOMAIN + aad + nonce + ciphertext)
        payload = json.loads(AESGCM(keys.link_aes_key).decrypt(nonce, ciphertext, aad))
    except Exception as e:  # noqa: BLE001 - orice problemă înseamnă același lucru: pachetul nu e de încredere
        raise SealError("bad_signature") from e
    if not isinstance(payload, dict):
        raise SealError("bad_signature")
    return payload
