"""Generează fișierele de predare pentru backend, din cod (nu pot rămâne în urmă):

    uv run --project backend python scripts/build_handoff.py

  backend/handoff/02_CONTRACT_ENDPOINTS.md   contractul compact: fiecare endpoint, rolurile, cererea, răspunsul, taskul
  backend/handoff/03_BAZA_DE_DATE.md         toate tabelele, coloanele, cheile, indecșii (din app/db/models)
  backend/handoff/04_SCHELET.md              fiecare fișier din backend/, ce face și taskul care îl implementează

Rulați-l după orice schimbare în routere, schemas.py, db/models sau după ce adăugați fișiere.
"""
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUT = BACKEND / "handoff"
sys.path.insert(0, str(BACKEND))


from app.db import models  # noqa: E402,F401  (înregistrează tabelele)
from app.db.base import Base  # noqa: E402
from app.main import app  # noqa: E402

# ---------------------------------------------------------------- endpoint → task
TASK_OF = [
    (r"^/health$", "T03"),
    (r"^/api/v1/auth/", "T07"),
    (r"^/api/v1/mission$|^/api/v1/environments$|^/api/v1/mission/environment$", "T09"),
    (r"^/api/v1/sim/clock$", "T33"),
    (r"^/api/v1/crew$", "T21"),
    (r"/dashboard$|/pillars/|/timeline$", "T21"),
    (r"^/api/v1/checkin|/checkins", "T18"),
    (r"/keystrokes/", "T19"),
    (r"/pvt$", "T20"),
    (r"/exercise/", "T28"),
    (r"^/api/v1/alerts|/alerts$|^/api/v1/cmo/queue$|^/api/v1/catalog/", "T17"),
    (r"^/api/v1/link/|^/api/v1/earth/replies$|/messages$", "T23"),
    (r"^/api/v1/radiation/", "T25"),
    (r"^/api/v1/sim/sep/", "T26"),
    (r"^/api/v1/ai/", "T31"),
    (r"^/api/v1/access-log$", "T08"),
    (r"^/api/v1/security/|^/api/v1/ingest/|^/api/v1/evidence/", "T32"),
    (r"^/api/v1/demo/|^/api/v1/sim/reset$", "T33"),
    (r"^/api/v1/events$", "T22"),
]


def task_for(path: str) -> str:
    return next((t for pat, t in TASK_OF if re.search(pat, path)), "—")


def ref_name(s: dict | None) -> str:
    if not s:
        return "—"
    if "$ref" in s:
        return s["$ref"].split("/")[-1]
    if s.get("type") == "array":
        return f"list[{ref_name(s.get('items'))}]"
    if "anyOf" in s:
        return " | ".join(ref_name(x) if x.get("type") != "null" else "null" for x in s["anyOf"])
    return s.get("type", "—")


spec = app.openapi()
lines = [
    "# 02 — Contractul endpoint-urilor (compact)",
    "",
    "**Generat** de `scripts/build_handoff.py` din `backend/app` (versiunea " + spec["info"]["version"] + "). Nu editați de mână.",
    "",
    "Versiunea completă, cu descrierea fiecărui câmp, exemple reale și regulile (roluri, erori, SSE, fluxuri):",
    "`contract/api/README.md`. Modelele: `backend/app/schemas.py`. Formatul erorilor: `{\"error\": {\"code\", \"message\", \"details\"}}`.",
    "",
    "Prefix: `/api/v1`. Autentificare: `Authorization: Bearer <token>` (în mock: `mock-<utilizator>`).",
    "Roluri: `astronaut` (doar datele lui), `cmo` (ofițerul medical; tot echipajul, cu jurnal), `earth` (doar pachetele sosite).",
    "",
    "| Metodă | Cale | Roluri | Cerere | Răspuns | Erori | Task |",
    "|---|---|---|---|---|---|---|",
]
by_task: dict[str, list[str]] = {}
for path, ops in spec["paths"].items():
    for method, op in ops.items():
        roles = ", ".join(op.get("x-roles", [])) or "public"
        body = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
        params = [f"{p['name']}" for p in op.get("parameters", []) if p["in"] == "query"]
        req = ref_name(body) if body else ""
        if params:
            req = (req + " · " if req else "") + "?" + "&".join(params)
        ok = next((c for c in op["responses"] if c.startswith("2")), "200")
        resp = ref_name(op["responses"][ok].get("content", {}).get("application/json", {}).get("schema"))
        if path.endswith("/events"):
            resp = "text/event-stream"
        errs = ",".join(c for c in op["responses"] if c[0] in "45" and c != "422") or "—"
        t = task_for(path)
        by_task.setdefault(t, []).append(f"`{method.upper()} {path}`")
        lines.append(f"| {method.upper()} | `{path}` | {roles} | {req or '—'} | `{ok}` {resp} | {errs} | {t} |")
lines += ["", "## Pe task", "", "| Task | Endpoint-uri |", "|---|---|"]
for t in sorted(by_task):
    lines.append(f"| {t} | " + ", ".join(by_task[t]) + " |")
lines += ["", "## Evenimente live (`GET /api/v1/events`)", "",
          "Plic: `{id, type, at, crew_id, data}`. Se publică **după commit**. Tipuri și forma lui `data`: `contract/api/README.md`, secțiunea 6.", ""]
sse_types = spec["components"]["schemas"]["SseEvent"]["properties"]["type"]["enum"]
lines.append(", ".join(f"`{t}`" for t in sse_types))
(OUT / "02_CONTRACT_ENDPOINTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

# ---------------------------------------------------------------- baza de date
db = [
    "# 03 — Baza de date",
    "",
    "**Generat** de `scripts/build_handoff.py` din `backend/app/db/models/`. Nu editați de mână; schimbați modelele.",
    "",
    "## Reguli",
    "",
    "- **SQLite, asincron** (`aiosqlite`), mod WAL, `foreign_keys=ON`, `busy_timeout=5000` (`app/db/session.py`).",
    "- **Fără migrări:** baza se șterge și se recreează la fiecare pornire (`RESET_DB_ON_START=true`), cu `create_all()`",
    "  și seed. Schimbi un model → repornești. Nu se comite niciun fișier `.sqlite`.",
    "- **Datele-oră** sunt `UTCDateTime`: refuză o dată fără fus orar; toate sunt **timp de misiune** (`clock.now()`).",
    "- **Id-urile** cu prefix (`al-0001`, `pk-0007`) le dă `app/ids.py` (contor în `sim_state`), în tranzacția scrierii.",
    "- **Relațiile** au `lazy=\"raise\"`: încărcați-le cu `selectinload(...)`. În asincron, accesul leneș dă eroare.",
    "- **Ordinea inserărilor:** fără relații ORM, într-un singur `flush()` ordinea nu e garantată. Inserați întâi",
    "  `crew`, apoi `await session.flush()`, apoi restul (altfel: `FOREIGN KEY constraint failed`).",
    "- **Câmpurile JSON** sunt pentru date citite întregi; tot ce apare într-un `WHERE` e coloană normală.",
    "- **Verificat** pe un fișier SQLite real: create_all, cheile străine, unicitatea check-in-ului pe zi,",
    "  unicitatea (direction, seq) a pachetelor (blochează replay-ul), relațiile cu `selectinload`, fusul orar UTC.",
    "",
    "## Tabelele",
    "",
]
mappers = sorted(Base.registry.mappers, key=lambda m: m.local_table.name)
for m in mappers:
    t = m.local_table
    db.append(f"### `{t.name}` — `{m.class_.__name__}` ({m.class_.__module__.split('.')[-1]}.py)")
    db.append("")
    if m.class_.__doc__:
        db.append(" ".join(m.class_.__doc__.split()))
        db.append("")
    import inspect as _inspect
    src = _inspect.getsource(m.class_)          # doar clasa, ca notițele să nu vină din altă clasă
    db.append("| Coloană | Tip | Null | Cheie | Implicit | Notă |")
    db.append("|---|---|---|---|---|---|")
    for c in t.columns:
        key = "PK" if c.primary_key else ""
        for fk in c.foreign_keys:
            key = (key + " " if key else "") + f"FK → `{fk.target_fullname}`"
        if c.unique:
            key += " unic"
        default = ""
        if c.default is not None and getattr(c.default, "arg", None) is not None and not callable(c.default.arg):
            default = f"`{c.default.arg!r}`"
        elif c.default is not None and callable(getattr(c.default, "arg", None)):
            default = "`[]`" if "list" in str(c.default.arg) else "auto"
        note = ""
        mm = re.search(rf"^\s+{c.name}: .*?#\s*(.+)$", src, re.M)
        if mm:
            note = mm.group(1).replace("|", "\\|")
        typ = type(c.type).__name__.replace("TypeDecorator", "")
        if hasattr(c.type, "length") and getattr(c.type, "length", None):
            typ += f"({c.type.length})"
        db.append(f"| `{c.name}` | {typ} | {'da' if c.nullable and not c.primary_key else 'nu'} | {key} | {default} | {note} |")
    extra = []
    for con in t.constraints:
        if con.__class__.__name__ == "UniqueConstraint" and len(con.columns) > 1:
            extra.append(f"UNIQUE ({', '.join(c.name for c in con.columns)})")
    for ix in t.indexes:
        extra.append(f"INDEX `{ix.name}` ({', '.join(c.name for c in ix.columns)})")
    rels = [f"`{r.key}` → {r.mapper.class_.__name__} (lazy={r.lazy})" for r in m.relationships]
    if extra:
        db.append("")
        db.append("Constrângeri și indecși: " + "; ".join(extra))
    if rels:
        db.append("")
        db.append("Relații: " + "; ".join(rels))
    db.append("")
(OUT / "03_BAZA_DE_DATE.md").write_text("\n".join(db) + "\n", encoding="utf-8")

# ---------------------------------------------------------------- scheletul
SKIP = {".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "handoff"}
sk = [
    "# 04 — Scheletul backend-ului",
    "",
    "**Generat** de `scripts/build_handoff.py`. Fiecare fișier din `backend/`, ce face și taskul care îl implementează.",
    "„gata” = funcționează deja; „mock” = răspunde cu date de exemplu până la taskul indicat; `Txx` = schelet",
    "(semnături + `NotImplementedError(\"Txx\")`).",
    "",
    "| Fișier | Stare | Ce face |",
    "|---|---|---|",
]


def describe(p: pathlib.Path) -> tuple[str, str]:
    text = p.read_text(encoding="utf-8")
    if p.suffix == ".py":
        try:
            doc = ast.get_docstring(ast.parse(text)) or ""
        except SyntaxError:
            doc = ""
        first = doc.strip().split("\n")[0] if doc else ""
        tasks = sorted(set(re.findall(r"NotImplementedError\(\"(T\d+)\"\)", text)))
        mt = re.search(r"TASK (T\d+)", doc)
        if tasks:
            state = ", ".join(tasks)
        elif "routers" in p.parts:
            state = "mock → " + (task_hint.get(p.stem, "—"))
        elif mt and "NotImplementedError" not in text and len(text.splitlines()) < 8:
            state = mt.group(1)
        else:
            state = "gata"
        return state, first.replace("|", "\\|")
    return "gata", {"pyproject.toml": "dependențele (uv)", "uv.lock": "versiunile exacte (se comite)",
                    ".python-version": "3.12", "users.json": "conturile de test, câte unul pe astronaut",
                    "README.md": "cum pornești", "PLAN_DE_ATAC_BACKEND.md": "planul: arhitectura, regulile, orele"}.get(p.name, "")


task_hint = {"auth": "T07", "mission": "T09", "crew": "T21", "checkin": "T18", "behavioral": "T19, T20",
             "exercise": "T28", "alerts": "T17", "link": "T23, T24", "radiation": "T25, T26", "ai": "T31",
             "security": "T08, T32", "demo": "T33", "events": "T22", "__init__": "—"}
for p in sorted(BACKEND.rglob("*")):
    rel = p.relative_to(BACKEND)
    if any(part in SKIP for part in rel.parts) or p.is_dir() or p.suffix in (".pyc", ".sqlite"):
        continue
    if p.name == "__init__.py" and p.stat().st_size == 0:
        continue
    state, what = describe(p)
    sk.append(f"| `backend/{rel.as_posix()}` | {state} | {what} |")
(OUT / "04_SCHELET.md").write_text("\n".join(sk) + "\n", encoding="utf-8")
print(f"ok: {sum(len(v) for v in spec['paths'].values())} endpoint-uri · {len(mappers)} tabele · {len(sk) - 8} fișiere")
