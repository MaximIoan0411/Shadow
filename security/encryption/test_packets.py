import copy
import os

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from packets import aes_key, canon, label, seal, unseal

alert = {"crew": "A1", "level": 3, "pillar": "immune"}

sealed = seal(alert, "A1", "2026-11-14")
assert unseal(sealed) == alert
print("Test 1 passed: Earth opens a real packet")

assert alert["pillar"] not in sealed["ct"] and "immune" not in str(sealed)
print("Test 2 passed: the packet content is not readable in transit")

broken = copy.deepcopy(sealed)
first = int(broken["ct"][:2], 16) ^ 1
broken["ct"] = f"{first:02x}" + broken["ct"][2:]
try:
    unseal(broken)
    print("Test 3 FAILED")
except InvalidTag:
    print("Test 3 passed: one changed byte is detected")

moved = copy.deepcopy(sealed)
moved["crew"] = "A2"
try:
    unseal(moved)
    print("Test 4 FAILED")
except InvalidTag:
    print("Test 4 passed: packet relabelled for another crew member is rejected")

try:
    unseal(sealed, key_name="storage")
    print("Test 5 FAILED")
except InvalidTag:
    print("Test 5 passed: the wrong key cannot open it")

fake_body = canon({"crew": "A1", "level": 1, "pillar": "immune"})
nonce = os.urandom(12)
forged_ct = AESGCM(aes_key("earthlink")).encrypt(nonce, os.urandom(64) + fake_body, label("A1", "2026-11-14"))
forged = {"crew": "A1", "day": "2026-11-14", "nonce": nonce.hex(), "ct": forged_ct.hex()}
try:
    unseal(forged)
    print("Test 6 FAILED")
except InvalidSignature:
    print("Test 6 passed: packet not signed by the ship is rejected")