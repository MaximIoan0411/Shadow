import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# keys come from security/keys/generate_keys.py; SHADOW_KEYS_DIR lets the tests use throwaway keys
KEYS_DIR = Path(os.environ.get("SHADOW_KEYS_DIR") or Path(__file__).resolve().parent.parent / "keys" / "keys_files")

# the only AES keys that exist; a typo in a key name is an error, not a new key
KEY_NAMES = ["earthlink", "storage"]


def canon(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def aes_key(name):
    if name not in KEY_NAMES:
        raise ValueError("Unknown key: " + str(name))
    return (KEYS_DIR / "private" / f"{name}.key").read_bytes()


SHIP_PRIVATE = serialization.load_pem_private_key(
    (KEYS_DIR / "private" / "ship.pem").read_bytes(), password=None)
SHIP_PUBLIC = serialization.load_pem_public_key(
    (KEYS_DIR / "public" / "ship.pem").read_bytes())


def label(crew, day):
    # JSON, not "a|b": ("A1|x", "d") and ("A1", "x|d") must not give the same label
    return canon(["shadow", crew, day])


def seal(packet, crew, day, key_name="earthlink"):
    body = canon(packet)
    # the signature also covers the label: whoever holds the link key cannot move
    # a signed packet to another crew member or another day
    signature = SHIP_PRIVATE.sign(label(crew, day) + body)
    nonce = os.urandom(12)
    ciphertext = AESGCM(aes_key(key_name)).encrypt(nonce, signature + body, label(crew, day))
    return {"crew": crew, "day": day, "nonce": nonce.hex(), "ct": ciphertext.hex()}


def unseal(message, key_name="earthlink"):
    plain = AESGCM(aes_key(key_name)).decrypt(
        bytes.fromhex(message["nonce"]),
        bytes.fromhex(message["ct"]),
        label(message["crew"], message["day"]),
    )
    signature, body = plain[:64], plain[64:]
    SHIP_PUBLIC.verify(signature, label(message["crew"], message["day"]) + body)
    return json.loads(body)


if __name__ == "__main__":
    alert = {"crew": "A1", "level": 3, "pillar": "immune", "note": "night pulse up 3 days"}
    sealed = seal(alert, "A1", "2026-11-14")
    print("Sealed packet to Earth:")
    print(json.dumps(sealed, indent=2)[:300], "...")
    print("Earth opened it:", unseal(sealed))
