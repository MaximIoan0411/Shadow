import json
import tempfile
from pathlib import Path

from audit import head, log_access, read_entries, verify, who_saw

folder = Path(tempfile.mkdtemp())

log = folder / "log1.jsonl"
log_access("medic", "medical_officer", "read alerts", "A1", log)
log_access("earth", "earth", "read level 3 packet", "A1", log)
log_access("comandant", "astronaut", "read own data", "A3", log)
assert verify(log) == (True, None)
print("Test 1 passed: untouched log is intact")

seen = [e["actor"] for e in who_saw("A1", log)]
assert seen == ["medic", "earth"]
print("Test 2 passed: A1 can see who opened their data ->", seen)

lines = log.read_text().splitlines()
entry = json.loads(lines[0])
entry["actor"] = "nobody"
lines[0] = json.dumps(entry)
log.write_text("\n".join(lines) + "\n")
ok, broken_at = verify(log)
assert not ok
print("Test 3 passed: edited entry detected, broken at entry", broken_at)

log2 = folder / "log2.jsonl"
for actor in ["medic", "earth", "medic"]:
    log_access(actor, "x", "read", "A1", log2)
lines = log2.read_text().splitlines()
del lines[1]
log2.write_text("\n".join(lines) + "\n")
ok, broken_at = verify(log2)
assert not ok
print("Test 4 passed: deleted entry detected, broken at entry", broken_at)

log3 = folder / "log3.jsonl"
for actor in ["medic", "earth", "medic"]:
    log_access(actor, "x", "read", "A1", log3)
anchor = head(log3)
assert verify(log3, anchor) == (True, None)
lines = log3.read_text().splitlines()
log3.write_text("\n".join(lines[:-1]) + "\n")
assert verify(log3) == (True, None)          # the chain alone cannot see a missing tail
ok, broken_at = verify(log3, anchor)
assert not ok and broken_at == 3
print("Test 5 passed: deleted last entry detected with the saved head, missing entry", broken_at)

log3.unlink()
for actor in ["nobody", "earth", "nobody"]:  # the whole log written again, with fresh hashes
    log_access(actor, "x", "read", "A1", log3)
ok, broken_at = verify(log3, anchor)
assert not ok
print("Test 6 passed: a log rewritten from scratch is detected with the saved head")

log_access("medic", "x", "read", "A1", log3)
assert verify(log3, head(log3)) == (True, None)
print("Test 7 passed: the log can keep growing after a head was saved")

log4 = folder / "log4.jsonl"
log_access("medic", "x", "read", "A1", log4)
log4.write_text(log4.read_text() + "{broken json\n")
assert verify(log4) == (False, 2)
print("Test 8 passed: a damaged line is reported, the check does not crash")
