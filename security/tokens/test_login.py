import sys
import time

import login as login_module
from login import LOCK_TIME, MAX_TRACKED, WINDOW, login
from tokens import check_token

# Test 1: each account gets the right role
expected = {"comandant": "astronaut", "specialist2": "astronaut",
            "medic": "medical_officer", "inginer": "astronaut", "earth": "earth"}
passwords = {"comandant": "cm1-shadow", "specialist2": "cm2-shadow",
             "medic": "cm3-shadow", "inginer": "cm4-shadow", "earth": "earth-shadow"}
for user, role in expected.items():
    claims = check_token(login(user, passwords[user]), [role])
    assert claims["role"] == role
print("Test 1 passed: all 5 accounts get the right role")

try:
    login("medic", "wrong")
    sys.exit("Test 2 FAILED")
except PermissionError:
    print("Test 2 passed: wrong password rejected")

for i in range(5):
    try:
        login("inginer", "guess" + str(i))
    except PermissionError:
        pass
try:
    login("inginer", "cm4-shadow")
    sys.exit("Test 3 FAILED")
except PermissionError as e:
    print("Test 3 passed: account locked ->", e)

try:
    login("hacker", "x")
    sys.exit("Test 4 FAILED")
except PermissionError as e:
    assert str(e) == "Wrong username or password."
    print("Test 4 passed: unknown user gets the same message as a wrong password ->", e)


def seconds_to_refuse(username):
    best = None
    for _ in range(3):
        login_module.failed.clear()
        login_module.locked_until.clear()
        start = time.perf_counter()
        try:
            login(username, "wrong")
        except PermissionError:
            pass
        spent = time.perf_counter() - start
        best = spent if best is None else min(best, spent)
    return best


real, unknown = seconds_to_refuse("medic"), seconds_to_refuse("nobody-here")
assert unknown > real / 2, (real, unknown)
print("Test 5 passed: an unknown user takes as long as a real one (%.0f ms vs %.0f ms)" % (unknown * 1000, real * 1000))

login_module.failed.clear()
login_module.locked_until.clear()
for i in range(5):
    try:
        login("inginer", "guess" + str(i))
    except PermissionError:
        pass
login_module.locked_until["inginer"] -= LOCK_TIME + 1      # as if the lock time had passed
check_token(login("inginer", "cm4-shadow"), ["astronaut"])
print("Test 6 passed: the account opens again after the lock time")

long_ago = time.monotonic() - WINDOW - 1
login_module.failed["medic"] = [long_ago] * 4
try:
    login("medic", "wrong")
except PermissionError:
    pass
check_token(login("medic", "cm3-shadow"), ["medical_officer"])
print("Test 7 passed: wrong tries older than 5 minutes do not count")

login_module.failed.clear()
login_module.failed.update({"ghost-" + str(i): [long_ago] for i in range(MAX_TRACKED + 50)})
try:
    login("medic", "wrong")
except PermissionError:
    pass
assert len(login_module.failed) == 1, len(login_module.failed)

just_now = time.monotonic()
login_module.failed.update({"flood-" + str(i): [just_now] for i in range(MAX_TRACKED + 50)})
try:
    login("medic", "wrong")
except PermissionError:
    pass
assert len(login_module.failed) <= MAX_TRACKED, len(login_module.failed)
print("Test 8 passed: made-up usernames do not pile up in memory")
