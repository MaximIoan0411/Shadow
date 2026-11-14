import copy
import sys
import time

from measurements import FROZEN_COUNT, MAX_AGE, Checker, Rejected, make_reading, sign_reading


def expect_rejected(test_name, checker, message, reason):
    try:
        checker.check(message)
    except Rejected as e:
        if str(e) != reason:
            sys.exit(test_name + " FAILED: wrong reason -> " + str(e))
        print(test_name, "passed:", reason)
        return
    sys.exit(test_name + " FAILED: it was accepted")


checker = Checker()

good = sign_reading(make_reading("hr-01", "A1", 58), "sensor-sim")
checker.check(good)
print("Test 1 passed: real reading accepted")

fake = copy.deepcopy(good)
fake["reading"]["hr"] = 140
fake["reading"]["nonce"] = "new-nonce-1"
expect_rejected("Test 2", checker, fake, "bad signature")

stolen = copy.deepcopy(good)
stolen["kid"] = "sensor-checkin"
expect_rejected("Test 3", checker, stolen, "bad signature")

expect_rejected("Test 4", checker, good, "replay")

impossible = sign_reading(make_reading("hr-01", "A1", 400), "sensor-sim")
expect_rejected("Test 5", checker, impossible, "impossible value")

old = make_reading("hr-01", "A1", 60)
old["ts"] = int(time.time()) - 600
expect_rejected("Test 6", checker, sign_reading(old, "sensor-sim"), "stale timestamp")

frozen_checker = Checker()
for i in range(20):
    frozen_checker.check(sign_reading(make_reading("hr-02", "A2", 72), "sensor-sim"))
stuck = sign_reading(make_reading("hr-02", "A2", 72), "sensor-sim")
expect_rejected("Test 7", frozen_checker, stuck, "frozen sensor")

unknown = copy.deepcopy(good)
unknown["kid"] = "hacker"
expect_rejected("Test 8", checker, unknown, "unknown key")

for number, broken in enumerate([None, {"kid": "sensor-sim"}, {"kid": "sensor-sim", "sig": "00"},
                                 {"kid": ["x"], "sig": "00", "reading": {}},
                                 {"kid": "sensor-sim", "sig": 5, "reading": {}}], start=1):
    expect_rejected("Test 9." + str(number), checker, broken, "malformed message")

busy = Checker()
for i in range(60):
    reading = make_reading("hr-03", "A3", 60 + i % 30)
    reading["ts"] -= MAX_AGE - 20                 # old, but still fresh enough to be accepted
    busy.check(sign_reading(reading, "sensor-sim"))
assert len(busy.history[("hr-03", "A3")]) == FROZEN_COUNT
real_time = time.time
time.time = lambda: real_time() + 60              # one minute later the 60 readings are stale
try:
    busy.check(sign_reading(make_reading("hr-03", "A3", 61), "sensor-sim"))
finally:
    time.time = real_time
assert len(busy.seen_nonces) == 1, len(busy.seen_nonces)
print("Test 10 passed: old values and old nonces are forgotten, memory stays small")
