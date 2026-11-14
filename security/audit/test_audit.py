import json
import tempfile
from pathlib import Path

from audit_log import log_access, read_entries, verify, who_saw

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