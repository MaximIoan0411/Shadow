import copy
import time

from measurements import Checker, Rejected, make_reading, sign_reading


def expect_rejected(test_name, checker, message, reason):
    try:
        checker.check(message)
        print(test_name, "FAILED: it was accepted")
    except Rejected as e:
        if str(e) == reason:
            print(test_name, "passed:", reason)
        else:
            print(test_name, "FAILED: wrong reason ->", e)


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
