"""Cheile. Se generează cu security/keys/generate_keys.py și NU intră în git.

| Cheie                 | Tip              | La ce folosește                     |
| a navei               | Ed25519          | semnează pachetele navă → Pământ    |
| a Pământului          | Ed25519          | semnează pachetele Pământ → navă    |
| a fiecărui dispozitiv | Ed25519          | semnează măsurătorile               |
| a legăturii           | AES-256 (32 B)   | criptează pachetele                 |
| a tokenurilor         | secret HS256     | semnează JWT-urile (din JWT_SECRET) |

Fișierele stau în `<keys_dir>/keys_files/` (`private/` și `public/`), sau în folderul din variabila de mediu
`SHADOW_KEYS_DIR` (folosită de teste, ca să nu atingă cheile reale). La pornire, cheile care lipsesc sunt create
cu `<keys_dir>/generate_keys.py`; o cheie existentă nu e niciodată înlocuită. Dacă o cheie nu poate fi nici citită,
nici creată, pornirea se oprește cu un mesaj clar.
"""
import base64
import binascii
import importlib.util
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from cryptography.hazmat.primitives import serialization

PROVIZORIU: tuple[str, ...] = ()
"""Funcțiile al căror corp e încă provizoriu. Echipa de securitate scoate numele pe măsură ce le termină."""

log = logging.getLogger("uvicorn.error")

_BACKEND_DIR = Path(__file__).resolve().parents[2]
KEYS_DIR_ENV = "SHADOW_KEYS_DIR"
GENERATOR = "generate_keys.py"
SHIP_KEY_ID = "ship-2026-01"
EARTH_KEY_ID = "earth-2026-01"
LINK_KEY_FILE = "earthlink.key"
AES_KEY_BYTES = 32

DEVICE_CREW: dict[str, str] = {f"wearable-cm-{i}": f"cm-{i}" for i in range(1, 5)}
"""Fiecare dispozitiv vorbește pentru UN singur membru al echipajului: device_id → crew_id."""


class KeysError(RuntimeError):
    """O cheie lipsește sau e stricată. Pornirea se oprește."""


@dataclass
class Keys:
    ship_key_id: str
    earth_key_id: str
    ship_private: bytes           # Ed25519, 32 de octeți
    earth_private: bytes
    link_aes_key: bytes
    device_public: dict[str, bytes] = field(default_factory=dict)   # device_id → cheia publică (32 de octeți)
    device_private: dict[str, bytes] = field(default_factory=dict)  # doar pentru simulatorul din prototip
    device_crew: dict[str, str] = field(default_factory=dict)       # device_id → singurul crew_id pentru care poate semna


def _files_dir(keys_dir: str) -> tuple[Path, Path]:
    base = Path(keys_dir)
    base = base if base.is_absolute() else (_BACKEND_DIR / base).resolve()
    override = os.environ.get(KEYS_DIR_ENV)
    return base, (Path(override) if override else base / "keys_files")


def _generate_missing(base: Path, files: Path) -> None:
    """Creează cheile care lipsesc, cu același script pe care îl rulează echipa de securitate."""
    script = base / GENERATOR
    if not script.exists():
        return
    spec = importlib.util.spec_from_file_location("shadow_generate_keys", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    created = module.generate(keys_dir=files, device_keys=sorted(DEVICE_CREW))
    if created:
        log.warning("SHADOW keys created in %s: %s", files, ", ".join(created))


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        raise KeysError(
            f"Missing key file: {path}. Run `python security/keys/generate_keys.py` from the repository root."
        ) from None


def _private(path: Path) -> bytes:
    try:
        key = serialization.load_pem_private_key(_read(path), password=None)
        return key.private_bytes(
            serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
        )
    except (ValueError, TypeError, AttributeError):
        raise KeysError(f"Unreadable Ed25519 private key: {path}.") from None


def _public(path: Path) -> bytes:
    try:
        key = serialization.load_pem_public_key(_read(path))
        return key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    except (ValueError, TypeError, AttributeError):
        raise KeysError(f"Unreadable Ed25519 public key: {path}.") from None


def _link_key(link_aes_key_b64: str, files: Path) -> bytes:
    if link_aes_key_b64:
        try:
            key = base64.b64decode(link_aes_key_b64, validate=True)
        except (binascii.Error, ValueError):
            raise KeysError("LINK_AES_KEY_B64 is not valid Base64.") from None
    else:
        key = _read(files / "private" / LINK_KEY_FILE)
    if len(key) != AES_KEY_BYTES:
        raise KeysError(f"The link key must have {AES_KEY_BYTES} bytes (AES-256), it has {len(key)}.")
    return key


def load_keys(*, link_aes_key_b64: str = "", keys_dir: str = "../security/keys") -> Keys:
    """Încarcă toate cheile la pornire (din lifespan). Rezultatul se ține în `app.state.keys`."""
    base, files = _files_dir(keys_dir)
    _generate_missing(base, files)
    private, public = files / "private", files / "public"
    device_private = {}
    for device in DEVICE_CREW:
        path = private / f"{device}.pem"
        if path.exists():
            device_private[device] = _private(path)
    return Keys(
        ship_key_id=SHIP_KEY_ID,
        earth_key_id=EARTH_KEY_ID,
        ship_private=_private(private / "ship.pem"),
        earth_private=_private(private / "earth.pem"),
        link_aes_key=_link_key(link_aes_key_b64, files),
        device_public={device: _public(public / f"{device}.pem") for device in DEVICE_CREW},
        device_private=device_private,
        device_crew=dict(DEVICE_CREW),
    )
