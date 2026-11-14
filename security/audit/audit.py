import hashlib
import json
import time
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent / "access_log.jsonl"
START = "0" * 64


def canon(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def read_entries(path=LOG_FILE):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def log_access(actor, role, action, target, path=LOG_FILE):
    entries = read_entries(path)
    previous = entries[-1]["hash"] if entries else START
    entry = {
        "n": len(entries) + 1,
        "ts": int(time.time()),
        "actor": actor,
        "role": role,
        "action": action,
        "target": target,
        "prev": previous,
    }
    entry["hash"] = hashlib.sha256(canon(entry)).hexdigest()
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def verify(path=LOG_FILE):
    previous = START
    for position, entry in enumerate(read_entries(path), start=1):
        body = {k: v for k, v in entry.items() if k != "hash"}
        good_hash = hashlib.sha256(canon(body)).hexdigest()
        if entry.get("n") != position or entry.get("prev") != previous or entry.get("hash") != good_hash:
            return False, position
        previous = entry["hash"]
    return True, None


def who_saw(target, path=LOG_FILE):
    return [e for e in read_entries(path) if e["target"] == target]


if __name__ == "__main__":
    ok, broken_at = verify()
    if ok:
        print("Access log intact:", len(read_entries()), "entries")
    else:
        print("ACCESS LOG TAMPERED: first broken entry is number", broken_at)