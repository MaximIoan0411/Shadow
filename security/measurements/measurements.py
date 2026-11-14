import json
import os
import time
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from pydantic import BaseModel, Field, ValidationError

KEYS_DIR = Path(__file__).resolve().parent.parent / "keys" / "keys_files"

SENSORS = ["sensor-keyboard", "sensor-checkin", "sensor-sim"]

MAX_AGE = 120
FROZEN_COUNT = 20


class Reading(BaseModel):
    sensor: str
    crew: str
    hr: int = Field(ge=25, le=230)
    ts: int
    nonce: str


class Rejected(Exception):
    pass


def canon(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def load_private(name):
    return serialization.load_pem_private_key(
        (KEYS_DIR / "private" / f"{name}.pem").read_bytes(), password=None)


def load_public(name):
    return serialization.load_pem_public_key(
        (KEYS_DIR / "public" / f"{name}.pem").read_bytes())


PUBLIC_KEYS = {name: load_public(name) for name in SENSORS}


def make_reading(sensor, crew, hr):
    return {
        "sensor": sensor,
        "crew": crew,
        "hr": hr,
        "ts": int(time.time()),
        "nonce": os.urandom(8).hex(),
    }


def sign_reading(reading, key_name):
    private_key = load_private(key_name)
    signature = private_key.sign(canon(reading)).hex()
    return {"kid": key_name, "reading": reading, "sig": signature}


class Checker:
    def __init__(self):
        self.seen_nonces = set()
        self.history = {}

    def check(self, message):
        kid = message.get("kid")
        if kid not in PUBLIC_KEYS:
            raise Rejected("unknown key")

        try:
            PUBLIC_KEYS[kid].verify(bytes.fromhex(message["sig"]),
                                    canon(message["reading"]))
        except (InvalidSignature, ValueError):
            raise Rejected("bad signature")

        try:
            reading = Reading(**message["reading"])
        except ValidationError:
            raise Rejected("impossible value")

        if abs(time.time() - reading.ts) > MAX_AGE:
            raise Rejected("stale timestamp")

        if reading.nonce in self.seen_nonces:
            raise Rejected("replay")

        key = (reading.sensor, reading.crew)
        last = self.history.setdefault(key, [])
        if len(last) >= FROZEN_COUNT and len(set(last[-FROZEN_COUNT:] + [reading.hr])) == 1:
            raise Rejected("frozen sensor")

        self.seen_nonces.add(reading.nonce)
        last.append(reading.hr)
        return reading


if __name__ == "__main__":
    checker = Checker()
    message = sign_reading(make_reading("hr-01", "A1", 58), "sensor-sim")
    print("Signed message:")
    print(json.dumps(message, indent=2))
    reading = checker.check(message)
    print("Accepted: crew", reading.crew, "pulse", reading.hr)
