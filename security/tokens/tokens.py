import time
import uuid
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization

ROLES = ["astronaut", "medical_officer", "earth"]

TOKEN_LIFE = 15 * 60

KEYS_DIR = Path(__file__).resolve().parent.parent / "keys" / "keys_files"

PRIVATE_KEY = serialization.load_pem_private_key(
    (KEYS_DIR / "private" / "auth.pem").read_bytes(), password=None)
PUBLIC_KEY = serialization.load_pem_public_key(
    (KEYS_DIR / "public" / "auth.pem").read_bytes())


def create_token(person, role):
    if role not in ROLES:
        raise ValueError("Unknown role: " + role)

    now = int(time.time())
    claims = {
        "sub": person,
        "role": role,
        "iat": now,
        "exp": now + TOKEN_LIFE,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(claims, PRIVATE_KEY, algorithm="EdDSA")


def check_token(token, allowed_roles):
    claims = jwt.decode(
        token,
        PUBLIC_KEY,
        algorithms=["EdDSA"],
        options={"require": ["exp", "sub", "role"]},
    )
    if claims["role"] not in allowed_roles:
        raise PermissionError("Role not allowed: " + claims["role"])
    return claims


if __name__ == "__main__":
    token = create_token("A1", "astronaut")
    print("Token for A1:")
    print(token)
    print()
    claims = check_token(token, ["astronaut"])
    print("Checked OK. Person:", claims["sub"], "| Role:", claims["role"])