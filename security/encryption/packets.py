import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEYS_DIR = Path(__file__).resolve().parent.parent / "keys" / "keys_files"


def canon(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def aes_key(name):
    path = KEYS_DIR / "private" / f"{name}.key"
    if not path.exists():
        path.write_bytes(os.urandom(32))
    return path.read_bytes()


SHIP_PRIVATE = serialization.load_pem_private_key(
    (KEYS_DIR / "private" / "ship.pem").read_bytes(), password=None)
SHIP_PUBLIC = serialization.load_pem_public_key(
    (KEYS_DIR / "public" / "ship.pem").read_bytes())


def label(crew, day):
    return f"shadow|{crew}|{day}".encode()


def seal(packet, crew, day, key_name="earthlink"):
    body = canon(packet)
    signature = SHIP_PRIVATE.sign(body)
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
    SHIP_PUBLIC.verify(signature, body)
    return json.loads(body)


if __name__ == "__main__":
    alert = {"crew": "A1", "level": 3, "pillar": "immune", "note": "night pulse up 3 days"}
    sealed = seal(alert, "A1", "2026-11-14")
    print("Sealed packet to Earth:")
    print(json.dumps(sealed, indent=2)[:300], "...")
    print("Earth opened it:", unseal(sealed))