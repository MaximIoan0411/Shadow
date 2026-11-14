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


def head(path=LOG_FILE):
    """The number and hash of the last entry. Keep it somewhere the log's writer cannot reach
    (for example in every packet sent to Earth) and give it back to verify()."""
    entries = read_entries(path)
    if not entries:
        return {"n": 0, "hash": START}
    return {"n": entries[-1]["n"], "hash": entries[-1]["hash"]}


def verify(path=LOG_FILE, anchor=None):
    """(True, None) if the log is intact, else (False, number of the first broken entry).

    The chain alone shows an edited or deleted entry in the middle. It cannot show that the LAST entries
    were deleted, or that the whole log was rewritten with fresh hashes. For that, pass an `anchor`:
    a head() saved earlier, outside the log."""
    previous = START
    position = 0
    lines = [line for line in path.read_text().splitlines() if line.strip()] if path.exists() else []
    for position, line in enumerate(lines, start=1):
        try:
            entry = json.loads(line)
        except ValueError:
            return False, position
        if not isinstance(entry, dict):
            return False, position
        body = {k: v for k, v in entry.items() if k != "hash"}
        good_hash = hashlib.sha256(canon(body)).hexdigest()
        if entry.get("n") != position or entry.get("prev") != previous or entry.get("hash") != good_hash:
            return False, position
        if anchor and position == anchor["n"] and entry["hash"] != anchor["hash"]:
            return False, position
        previous = entry["hash"]
    if anchor and position < anchor["n"]:
        return False, position + 1
    return True, None


def who_saw(target, path=LOG_FILE):
    return [e for e in read_entries(path) if e["target"] == target]


if __name__ == "__main__":
    ok, broken_at = verify()
    if ok:
        print("Access log intact:", len(read_entries()), "entries")
    else:
        print("ACCESS LOG TAMPERED: first broken entry is number", broken_at)
