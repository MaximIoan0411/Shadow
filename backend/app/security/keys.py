"""Cheile. Se generează cu security/keys/generate_keys.py și NU intră în git.

| Cheie                 | Tip              | La ce folosește                     |
| a navei               | Ed25519          | semnează pachetele navă → Pământ    |
| a Pământului          | Ed25519          | semnează pachetele Pământ → navă    |
| a fiecărui dispozitiv | Ed25519          | semnează măsurătorile               |
| a legăturii           | AES-256 (32 B)   | criptează pachetele                 |
| a tokenurilor         | secret HS256     | semnează JWT-urile (din JWT_SECRET) |
"""
import os
from dataclasses import dataclass, field

PROVIZORIU: tuple[str, ...] = ('load_keys',)
"""Funcțiile al căror corp e încă provizoriu. Echipa de securitate scoate numele pe măsură ce le termină."""


@dataclass
class Keys:
    ship_key_id: str
    earth_key_id: str
    ship_private: bytes
    earth_private: bytes
    link_aes_key: bytes
    device_public: dict[str, bytes] = field(default_factory=dict)   # device_id → cheia publică


# PROVIZORIU: dacă nu există chei, generează octeți aleatori în memorie, ca backend-ul să pornească.
# Varianta reală încarcă din fișierele generate și OPREȘTE pornirea dacă lipsește o cheie.
def load_keys(*, link_aes_key_b64: str = "", keys_dir: str = "../security/keys") -> Keys:
    """Încarcă toate cheile la pornire (din lifespan). Rezultatul se ține în `app.state.keys`."""
    import base64
    aes = base64.b64decode(link_aes_key_b64) if link_aes_key_b64 else os.urandom(32)
    return Keys(ship_key_id="ship-2026-01", earth_key_id="earth-2026-01",
                ship_private=os.urandom(32), earth_private=os.urandom(32), link_aes_key=aes,
                device_public={f"wearable-cm-{i}": os.urandom(32) for i in range(1, 5)})
