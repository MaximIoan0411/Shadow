import base64
import json
import sys
import time

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tokens import PRIVATE_KEY, check_token, create_token


def b64(data):
    text = json.dumps(data).encode()
    return base64.urlsafe_b64encode(text).rstrip(b"=").decode()


token = create_token("A1", "astronaut")
check_token(token, ["astronaut"])
print("Test 1 passed: real token accepted")

try:
    check_token(token, ["medical_officer"])
    sys.exit("Test 2 FAILED")
except PermissionError:
    print("Test 2 passed: wrong role rejected")

header, payload, signature = token.split(".")
fake_payload = b64({"sub": "A1", "role": "medical_officer",
                    "exp": int(time.time()) + 900})
try:
    check_token(header + "." + fake_payload + "." + signature, ["medical_officer"])
    sys.exit("Test 3 FAILED")
except jwt.InvalidTokenError:
    print("Test 3 passed: changed token rejected")

none_token = b64({"alg": "none", "typ": "JWT"}) + "." + fake_payload + "."
try:
    check_token(none_token, ["medical_officer"])
    sys.exit("Test 4 FAILED")
except jwt.InvalidTokenError:
    print("Test 4 passed: unsigned token rejected")

expired = jwt.encode({"sub": "A1", "role": "astronaut", "exp": int(time.time()) - 10},
                     PRIVATE_KEY, algorithm="EdDSA")
try:
    check_token(expired, ["astronaut"])
    sys.exit("Test 5 FAILED")
except jwt.ExpiredSignatureError:
    print("Test 5 passed: expired token rejected")

forged = jwt.encode({"sub": "A1", "role": "medical_officer", "exp": int(time.time()) + 900},
                    Ed25519PrivateKey.generate(), algorithm="EdDSA")
try:
    check_token(forged, ["medical_officer"])
    sys.exit("Test 6 FAILED")
except jwt.InvalidTokenError:
    print("Test 6 passed: token signed with someone else's key rejected")
