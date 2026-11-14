import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# keys come from security/keys/generate_keys.py; SHADOW_KEYS_DIR lets the tests use throwaway keys
KEYS_DIR = Path(os.environ.get("SHADOW_KEYS_DIR") or Path(__file__).resolve().parent.parent / "keys" / "keys_files")

STORAGE_KEY = (KEYS_DIR / "private" / "storage.key").read_bytes()


def encrypt_record(record, crew):
    nonce = os.urandom(12)
    data = json.dumps(record).encode()
    ciphertext = AESGCM(STORAGE_KEY).encrypt(nonce, data, crew.encode())
    return {"crew": crew, "nonce": nonce.hex(), "ct": ciphertext.hex()}


def decrypt_record(stored):
    data = AESGCM(STORAGE_KEY).decrypt(
        bytes.fromhex(stored["nonce"]),
        bytes.fromhex(stored["ct"]),
        stored["crew"].encode(),
    )
    return json.loads(data)


if __name__ == "__main__":
    checkin = {"crew": "A1", "bp": "118/76", "hr": 62, "glucose": 92, "temp": 36.7, "mood": 4}
    stored = encrypt_record(checkin, "A1")
    print("Saved in the database:", stored["ct"][:60], "...")
    print("Read back:", decrypt_record(stored))
