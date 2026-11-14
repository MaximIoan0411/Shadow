import copy

from cryptography.exceptions import InvalidTag

from storage import decrypt_record, encrypt_record

checkin = {"crew": "A1", "hr": 62, "glucose": 92}

stored = encrypt_record(checkin, "A1")
assert decrypt_record(stored) == checkin
print("Test 1 passed: record saved and read back")

assert "glucose" not in str(stored)
print("Test 2 passed: stored record is not readable")

again = encrypt_record(checkin, "A1")
assert again["ct"] != stored["ct"]
print("Test 3 passed: same data encrypts differently each time")

changed = copy.deepcopy(stored)
first = int(changed["ct"][:2], 16) ^ 1
changed["ct"] = f"{first:02x}" + changed["ct"][2:]
try:
    decrypt_record(changed)
    print("Test 4 FAILED")
except InvalidTag:
    print("Test 4 passed: changed record detected")

swapped = copy.deepcopy(stored)
swapped["crew"] = "A2"
try:
    decrypt_record(swapped)
    print("Test 5 FAILED")
except InvalidTag:
    print("Test 5 passed: record moved to another crew member is rejected")