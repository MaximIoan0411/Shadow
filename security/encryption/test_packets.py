import copy
import os
import sys

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from packets import KEYS_DIR, aes_key, canon, label, seal, unseal

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
    sys.exit("Test 3 FAILED")
except InvalidTag:
    print("Test 3 passed: one changed byte is detected")

moved = copy.deepcopy(sealed)
moved["crew"] = "A2"
try:
    unseal(moved)
    sys.exit("Test 4 FAILED")
except InvalidTag:
    print("Test 4 passed: packet relabelled for another crew member is rejected")

try:
    unseal(sealed, key_name="storage")
    sys.exit("Test 5 FAILED")
except InvalidTag:
    print("Test 5 passed: the wrong key cannot open it")

fake_body = canon({"crew": "A1", "level": 1, "pillar": "immune"})
nonce = os.urandom(12)
forged_ct = AESGCM(aes_key("earthlink")).encrypt(nonce, os.urandom(64) + fake_body, label("A1", "2026-11-14"))
forged = {"crew": "A1", "day": "2026-11-14", "nonce": nonce.hex(), "ct": forged_ct.hex()}
try:
    unseal(forged)
    sys.exit("Test 6 FAILED")
except InvalidSignature:
    print("Test 6 passed: packet not signed by the ship is rejected")

# someone who holds the link key opens a real packet and re-labels it for another crew member and day
key = aes_key("earthlink")
plain = AESGCM(key).decrypt(bytes.fromhex(sealed["nonce"]), bytes.fromhex(sealed["ct"]), label("A1", "2026-11-14"))
nonce = os.urandom(12)
relabelled = {"crew": "A2", "day": "2026-12-01", "nonce": nonce.hex(),
              "ct": AESGCM(key).encrypt(nonce, plain, label("A2", "2026-12-01")).hex()}
try:
    unseal(relabelled)
    sys.exit("Test 7 FAILED")
except InvalidSignature:
    print("Test 7 passed: the ship's signature also covers the crew member and the day")

assert label("A1|x", "d") != label("A1", "x|d")
print("Test 8 passed: two different labels never look the same")

before = sorted(path.name for path in (KEYS_DIR / "private").iterdir())
for bad_name in ["earthlnik", "../escaped"]:
    try:
        seal(alert, "A1", "2026-11-14", key_name=bad_name)
        sys.exit("Test 9 FAILED")
    except ValueError:
        pass
assert sorted(path.name for path in (KEYS_DIR / "private").iterdir()) == before
assert not (KEYS_DIR / "escaped.key").exists()
print("Test 9 passed: an unknown key name is an error, no key file is created")
