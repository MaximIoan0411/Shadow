"""Verifică toate contractele. Rulați înainte de fiecare PR:

    uv run --project backend python scripts/smoke.py

1. API: fiecare endpoint răspunde 2xx cu cererea lui de exemplu; regulile de permisiuni; regulile din 1.2.
2. Conturi separate pe astronaut, blocarea după parole greșite.
3. Data: toate fișierele din data/ respectă datafiles.py.
4. AI: ai/service/schemas.py și backend/app/ai_schemas.py sunt identice; mock-ul AI răspunde după contract.
5. Securitate: modulele din backend/app/security/ au exact funcțiile din contract.
"""
import inspect
import os
import pathlib
import sys

os.environ.setdefault("BACKGROUND_TASKS", "false")  # the contract check needs no live loops
os.environ["ALLOW_MOCK_TOKENS"] = "true"  # smoke signs in with mock-<user> tokens
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "ai"))
sys.path.insert(0, str(ROOT / "scripts"))
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from app.datafiles import load_all  # noqa: E402
from app.main import app  # noqa: E402
from request_examples import AI_REQUESTS, REQUESTS  # noqa: E402

c = TestClient(app).__enter__()   # runs the app's startup (database, seed, history replay)
H = lambda r: {"Authorization": f"Bearer mock-{r}"} if r else {}


def real_alert_ids():
    """The mock ids in request_examples.py -> the real alerts the engine produces at startup:
    al-1042 = cm-2's immune alert (level 2), al-1039 = cm-2's typing alert (level 1, active)."""
    mine = {a["topic"]: a["id"] for a in c.get("/api/v1/crew/cm-2/alerts", headers=H("specialist2")).json()}
    return {"al-1042": mine["immune"], "al-1039": mine["behavioral"]}


IDS = real_alert_ids()


def real(v):
    """Replaces the mock ids with real ones; pk-0006 / pk-0007 = the newest real packet to Earth (created by the
    level 3 escalation example, which runs before the packet examples)."""
    if isinstance(v, dict):
        return {k: real(x) for k, x in v.items()}
    if v in ("pk-0006", "pk-0007"):
        return c.get("/api/v1/link/packets?direction=down", headers=H("earth")).json()[0]["id"]
    return IDS.get(v, v) if isinstance(v, str) else v
ops = {(m.upper(), p) for p, v in app.openapi()["paths"].items() for m in v}
missing = ops - set(REQUESTS) - {("GET", "/api/v1/events")}
assert not missing, f"fără exemplu: {missing}"
for (m, tpl), r in REQUESTS.items():
    url = tpl.format(**real(r.get("path", {})))
    res = c.request(m, url, params=r.get("query"), json=real(r.get("json")), headers=H(r["as_"]))
    assert res.status_code < 300, (m, url, res.status_code, res.text[:300])
# permisiuni
assert c.get("/api/v1/mission").status_code == 401
assert c.get("/api/v1/crew/cm-1/dashboard", headers=H("specialist2")).status_code == 403
assert c.get("/api/v1/crew/cm-2/dashboard", headers=H("earth")).status_code == 403
assert c.get("/api/v1/radiation/status", headers=H("earth")).status_code == 403
assert c.get("/api/v1/cmo/queue", headers=H("specialist2")).status_code == 403
assert c.post(f"/api/v1/alerts/{IDS['al-1042']}/escalate", json={"to_level": 3}, headers=H("specialist2")).status_code == 403
r = c.post("/api/v1/crew/cm-2/keystrokes/batches", headers=H("specialist2"), json={"session_id": "x", "context": "demo", "events": [{"t_down_ms": 1, "t_up_ms": 2, "key_class": "char", "key": "a"}]})
assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error", r.text
assert c.get("/api/v1/nu-exista").json()["error"]["code"] == "not_found"
# conturi separate pe astronaut
import json  # noqa: E402

SEED = json.loads((ROOT / "backend" / "seed" / "users.json").read_text(encoding="utf-8"))["users"]
PASSWORDS = {u["username"]: u["test_password"] for u in SEED}   # the test accounts, from the seed (no mock)
CREW_OF = {u["username"]: u["crew_id"] for u in SEED}
accs = c.get("/api/v1/auth/accounts").json()
assert len(accs) == 5 and sum(a["role"] == "astronaut" for a in accs) == 3
crew_ids = [a["crew_id"] for a in accs if a["crew_id"]]
assert len(crew_ids) == len(set(crew_ids)) == 4, "fiecare cont de la bord are alt crew_id"
for username, pw in PASSWORDS.items():
    r = c.post("/api/v1/auth/login", json={"username": username, "password": pw})
    assert r.status_code == 200 and r.json()["user"]["username"] == username
    other = next(p for u, p in PASSWORDS.items() if u != username)
    assert c.post("/api/v1/auth/login", json={"username": username, "password": other}).status_code == 401, "parola altui cont nu merge"
for u in ("comandant", "specialist2", "inginer"):                      # fiecare își vede doar datele lui
    own = CREW_OF[u]
    d_ = c.get(f"/api/v1/crew/{own}/dashboard", headers=H(u))
    assert d_.status_code == 200 and d_.json()["crew"]["id"] == own
    for other in ("cm-1", "cm-2", "cm-3", "cm-4"):
        if other != own:
            assert c.get(f"/api/v1/crew/{other}/dashboard", headers=H(u)).status_code == 403
assert c.get(f"/api/v1/alerts/{IDS['al-1042']}", headers=H("comandant")).status_code == 403      # alerta lui cm-2
assert c.get("/api/v1/crew/cm-2/dashboard", headers=H("medic")).status_code == 200     # ofițerul medical are voie
c.post("/api/v1/sim/reset", headers=H("medic"))
for _ in range(5):
    assert c.post("/api/v1/auth/login", json={"username": "inginer", "password": "gresit"}).status_code == 401
r = c.post("/api/v1/auth/login", json={"username": "inginer", "password": PASSWORDS["inginer"]})
assert r.status_code == 429 and r.json()["error"]["code"] == "too_many_attempts", r.text
assert c.post("/api/v1/auth/login", json={"username": "comandant", "password": PASSWORDS["comandant"]}).status_code == 200  # blocarea e pe cont
c.post("/api/v1/sim/reset", headers=H("medic"))
# ---------------------------------------------------------------- reguli noi în 1.2
assert c.post("/api/v1/sim/reset", headers=H("medic")).status_code == 200
tl = c.get("/api/v1/crew/cm-2/timeline", headers=H("specialist2")).json()
assert tl["days"][-1]["day"] == 96, "derulatorul se oprește la ziua curentă"
r = c.get("/api/v1/crew/cm-2/dashboard?as_of_day=120", headers=H("specialist2"))
assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
r = c.put("/api/v1/sim/clock", json={"mission_day": 50}, headers=H("medic"))
assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_state"
assert c.get("/api/v1/mission", headers=H("medic")).json()["mission_day"] == 96

# ---------------------------------------------------------------- data/
data = load_all()
assert len(data.catalog.recommendations) >= 4 and data.scenario.start_day == 96
assert c.get("/api/v1/checkin/schema", headers=H("specialist2")).json()["indicators"][0]["key"] == "mood"

# ---------------------------------------------------------------- contractul AI: cele două copii sunt identice
from app import ai_schemas as be_ai  # noqa: E402
from service import schemas as ai_ai  # noqa: E402
from service.main import app as ai_app  # noqa: E402


def models(mod):
    return {n: o.model_json_schema() for n, o in vars(mod).items()
            if isinstance(o, type) and issubclass(o, BaseModel) and o is not BaseModel and o.__module__ == mod.__name__}


a, b = models(be_ai), models(ai_ai)
assert a == b, f"backend/app/ai_schemas.py diferă de ai/service/schemas.py: {sorted(set(a) ^ set(b)) or [n for n in a if a[n] != b.get(n)]}"
ai_c = TestClient(ai_app)
for (m, url), r_ in AI_REQUESTS.items():
    res = ai_c.request(m, url, json=r_.get("json"))
    assert res.status_code < 300, (m, url, res.text[:200])
ai_ops = {(m.upper(), p) for p, v in ai_app.openapi()["paths"].items() for m in v}
assert ai_ops == set(AI_REQUESTS), f"endpoint AI fără exemplu: {ai_ops - set(AI_REQUESTS)}"

# ---------------------------------------------------------------- contractul de securitate: funcțiile există
import importlib  # noqa: E402

SECURITY_CONTRACT = {
    "passwords": {"hash": False, "verify": False},
    "tokens": {"issue": False, "decode": False, "revoke": True, "is_revoked": True},
    "lockout": {"check": False, "record_failure": False, "clear": False, "reset_all": False},
    "keys": {"load_keys": False},
    "signing": {"canonical": False, "sign": False, "verify": False},
    "sealing": {"seal": False, "open": False},
    "validation": {"check": False},
    "access_log": {"write": True, "verify_chain": True, "entry_hash": False},
}
for mod_name, fns in SECURITY_CONTRACT.items():
    mod = importlib.import_module(f"app.security.{mod_name}")
    for fn, is_async in fns.items():
        f = getattr(mod, fn, None)
        assert callable(f), f"security/{mod_name}.py: lipsește {fn}()"
        assert inspect.iscoroutinefunction(f) == is_async, f"security/{mod_name}.{fn}: trebuie să fie {'async' if is_async else 'sync'}"
n_prov = sum(len(getattr(importlib.import_module(f"app.security.{m}"), "PROVIZORIU", ())) for m in SECURITY_CONTRACT)
for exc in ("InvalidToken", "AccountLocked", "SealError"):
    assert hasattr(importlib.import_module("app.security.errors"), exc), f"security/errors.py: lipsește {exc}"

print(f"OK: API {len(REQUESTS)} endpoint-uri + permisiuni + conturi separate + reguli 1.2 · "
      f"data {len(data.catalog.recommendations)} recomandări · AI {len(a)} modele identice · "
      f"securitate {sum(len(v) for v in SECURITY_CONTRACT.values())} funcții ({n_prov} încă provizorii)")
