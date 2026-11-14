"""Generează tot folderul contract/ din cod.

    uv run --project backend python scripts/build_docs.py

Ce produce:
  contract/api/       openapi.json, openapi.yaml, README.md   ← frontend ↔ backend (din backend/app)
  contract/ai/        openapi.json, openapi.yaml, README.md   ← backend ↔ serviciul AI (din ai/service)
  contract/security/  README.md                               ← backend ↔ securitate (din backend/app/security)
  contract/data/      schemas/*.schema.json, README.md        ← backend ↔ data/ (din backend/app/datafiles.py)

Partea scrisă de mână a fiecărui README stă în guide.md, lângă el. Se editează guide.md, NU README.md.
Rulați scriptul după ORICE schimbare în schemas.py, routere, ai_schemas.py, security/ sau datafiles.py."""
import inspect
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "ai"))
sys.path.insert(0, str(ROOT / "scripts"))

import yaml  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from app import datafiles, schemas  # noqa: E402
from app.main import app  # noqa: E402
from request_examples import AI_REQUESTS, REQUESTS  # noqa: E402
from service import main as ai_main  # noqa: E402
from service import schemas as ai_schemas  # noqa: E402

CONTRACT = ROOT / "contract"
ROLE_RO = {"astronaut": "astronaut", "cmo": "ofițer medical (cmo)", "earth": "Pământ (earth)",
           "public": "fără autentificare", "device": "dispozitiv (semnătură Ed25519, fără JWT)"}


# ===================================================================== utilitare comune
def shorten(o, keep=2):
    """Scurtează listele lungi din exemple, ca documentația să rămână lizibilă."""
    if isinstance(o, list):
        out = [shorten(x, keep) for x in o[:keep]]
        if len(o) > keep:
            out.append(f"… încă {len(o) - keep} elemente de același fel")
        return out
    if isinstance(o, dict):
        return {k: shorten(v, keep) for k, v in o.items()}
    return o


def jblock(o) -> str:
    return "```json\n" + json.dumps(o, ensure_ascii=False, indent=2) + "\n```"


def type_of(s: dict) -> str:
    if "$ref" in s:
        n = s["$ref"].split("/")[-1]
        return f"[{n}](#{n.lower()})"
    if "anyOf" in s:
        parts = [type_of(x) for x in s["anyOf"] if x.get("type") != "null"]
        nullable = any(x.get("type") == "null" for x in s["anyOf"])
        return " \\| ".join(parts) + (" \\| null" if nullable else "")
    if "allOf" in s:
        return type_of(s["allOf"][0])
    if "enum" in s:
        return " \\| ".join(f"`{json.dumps(v, ensure_ascii=False)}`" for v in s["enum"])
    if "const" in s:
        return f"`{json.dumps(s['const'])}`"
    if "prefixItems" in s:
        return "pereche (" + ", ".join(type_of(x) for x in s["prefixItems"]) + ")"
    t = s.get("type")
    if t == "array":
        return f"listă de {type_of(s.get('items', {}))}"
    if t == "object":
        ap = s.get("additionalProperties")
        return f"obiect {{cheie: {type_of(ap)}}}" if isinstance(ap, dict) and ap else "obiect"
    if t == "string":
        return "dată-oră (ISO 8601)" if s.get("format") == "date-time" else "text"
    return {"integer": "număr întreg", "number": "număr", "boolean": "true/false", None: "orice"}.get(t, str(t))


def constraints(s: dict) -> str:
    c = []
    for src in [s] + [x for x in s.get("anyOf", []) if isinstance(x, dict)]:
        for k, lab in (("minimum", "min"), ("maximum", "max"), ("exclusiveMinimum", ">"), ("minLength", "lungime min"),
                       ("maxLength", "lungime max"), ("minItems", "min elemente"), ("maxItems", "max elemente"),
                       ("pattern", "format")):
            if k in src:
                c.append(f"{lab} {src[k]}")
    return "; ".join(dict.fromkeys(c))


def enum_comments(module, name: str) -> dict[str, str]:
    src = pathlib.Path(module.__file__).read_text(encoding="utf-8")
    if f"class {name}(" not in src:
        return {}
    block = src.split(f"class {name}(")[1].split("\nclass ")[0]
    out = {}
    for line in block.splitlines():
        if "=" in line and "#" in line:
            out[line.split("=")[1].split("#")[0].strip().strip('"')] = line.split("#", 1)[1].strip()
    return out


def render_models(defs: dict, order_module=None, skip=("HTTPValidationError", "ValidationError")) -> str:
    names = list(defs)
    if order_module is not None:
        first = [n for n, o in vars(order_module).items() if isinstance(o, type) and n in defs]
        names = first + [n for n in names if n not in first]
    enums = [(n, defs[n]) for n in names if n not in skip and "enum" in defs[n]]
    objs = [(n, defs[n]) for n in names if n not in skip and "enum" not in defs[n]]
    out = []
    if enums:
        out.append("### Enumerări (valori fixe)\n")
        for name, s in enums:
            out.append(f"#### {name}\n")
            if s.get("description"):
                out.append(s["description"].strip() + "\n")
            comments = enum_comments(order_module or schemas, name)
            out.append("| Valoare | Înseamnă |\n|---|---|")
            out += [f"| `{v}` | {comments.get(str(v), '')} |" for v in s["enum"]]
            out.append("")
    out.append("### Obiecte\n")
    for name, s in objs:
        out.append(f"#### {name}\n")
        if s.get("description"):
            out.append(s["description"].strip() + "\n")
        props, req = s.get("properties", {}), set(s.get("required", []))
        if not props:
            continue
        out.append("| Câmp | Tip | Obligatoriu | Descriere |\n|---|---|---|---|")
        for k, p in props.items():
            d = (p.get("description") or "").replace("\n", " ").replace("|", "\\|")
            cons = constraints(p)
            exs = p.get("examples")
            extra = (f" ({cons})" if cons else "") + (f" Ex.: `{json.dumps(exs[0], ensure_ascii=False)}`" if exs else "")
            out.append(f"| `{k}` | {type_of(p)} | {'da' if k in req else 'nu'} | {d}{extra} |")
        out.append("")
    return "\n".join(out), len(enums), len(objs)


def render_reference(spec: dict, client: TestClient, requests: dict, auth: bool) -> tuple[str, str, int]:
    ref, toc, by_tag = [], [], {}
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            by_tag.setdefault(op.get("tags", ["Endpoint-uri"])[0], []).append((method.upper(), path, op))

    def tag_key(t):
        head = t.split(".")[0]
        return int(head) if head.isdigit() else 99

    for tag in sorted(by_tag, key=tag_key):
        anchor = tag.lower().replace(". ", "-").replace(" ", "-").replace(",", "").replace("(", "").replace(")", "")
        toc.append(f"- [{tag}](#{anchor})")
        ref.append(f"### {tag}\n")
        for method, path, op in by_tag[tag]:
            ref.append(f"#### `{method} {path}` — {op['summary']}\n")
            if auth:
                r = op.get("x-roles")
                ref.append("**Cine poate apela:** " + (", ".join(ROLE_RO[x] for x in r) if r else "oricine, fără autentificare") + "\n")
            desc = op.get("description", "")
            if desc.startswith("**Roluri permise:**"):
                desc = desc.split("\n\n", 1)[1] if "\n\n" in desc else ""
            if desc:
                ref.append(desc.strip() + "\n")
            params = [p for p in op.get("parameters", []) if p["name"] != "authorization"]
            if params:
                ref.append("| Parametru | Unde | Tip | Obligatoriu | Descriere |\n|---|---|---|---|---|")
                for p in params:
                    sch = p.get("schema", {})
                    d = (p.get("description") or sch.get("description") or "").replace("\n", " ")
                    dflt = f" Implicit: `{sch['default']}`." if sch.get("default") is not None else ""
                    cons = constraints(sch)
                    ref.append(f"| `{p['name']}` | {'cale' if p['in'] == 'path' else 'query'} | {type_of(sch)} | "
                               f"{'da' if p.get('required') else 'nu'} | {d}{dflt}{(' (' + cons + ')') if cons else ''} |")
                ref.append("")
            body = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
            if body:
                ref.append(f"**Corpul cererii:** {type_of(body)}\n")
            ok = next((c for c in op["responses"] if c.startswith("2")), "200")
            rs = op["responses"][ok].get("content", {}).get("application/json", {}).get("schema")
            ref.append(f"**Răspuns {ok}:** {type_of(rs) if rs else 'flux `text/event-stream`'}\n")
            errs = [c for c in op["responses"] if c[0] in "45"]
            if errs:
                ref.append("**Erori posibile:** " + ", ".join(errs) + " — forma din secțiunea [Erori](#5-erori).\n" if auth
                           else "**Erori posibile:** " + ", ".join(errs) + "\n")
            ex = requests.get((method, path))
            if ex:
                url = path.format(**ex.get("path", {}))
                q = ex.get("query")
                headers = {"Authorization": f"Bearer mock-{ex['as_']}"} if ex.get("as_") else {}
                res = client.request(method, url, params=q, json=ex.get("json"), headers=headers)
                assert res.status_code < 300, (method, url, res.status_code, res.text[:200])
                shown = url + ("?" + "&".join(f"{k}={str(v).lower() if isinstance(v, bool) else v}" for k, v in q.items()) if q else "")
                who = f" (autentificat ca <code>{ex['as_'] or 'nimeni'}</code>)" if auth else ""
                ref.append(f"<details><summary>Exemplu{who}</summary>\n")
                ref.append(f"```http\n{method} {shown}\n```\n")
                if ex.get("json") is not None:
                    ref.append("Cerere:\n\n" + jblock(ex["json"]) + "\n")
                ref.append(f"Răspuns `{res.status_code}`:\n\n" + jblock(shorten(res.json())) + "\n")
                ref.append("</details>\n")
            ref.append("---\n")
    n_ops = sum(len(v) for v in spec["paths"].values())
    return "\n".join(ref), "\n".join(toc), n_ops


def write_spec(folder: pathlib.Path, spec: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "openapi.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (folder / "openapi.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")


def fill(guide_path: pathlib.Path, **parts) -> str:
    text = guide_path.read_text(encoding="utf-8")
    for k, v in parts.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


# ===================================================================== 1. API: frontend ↔ backend
api_spec = app.openapi()
write_spec(CONTRACT / "api", api_spec)
api_client = TestClient(app)
ref, toc, n_ops = render_reference(api_spec, api_client, REQUESTS, auth=True)
models, n_en, n_ob = render_models(api_spec["components"]["schemas"], schemas)
(CONTRACT / "api" / "README.md").write_text(
    fill(CONTRACT / "api" / "guide.md", N_OPS=n_ops, N_MODELS=n_en + n_ob, VERSION=api_spec["info"]["version"],
         REF_TOC=toc, REFERENCE=ref, MODELS=models), encoding="utf-8")

# ===================================================================== 2. AI: backend ↔ serviciul AI
ai_spec = ai_main.app.openapi()
write_spec(CONTRACT / "ai", ai_spec)
ref_ai, toc_ai, n_ai = render_reference(ai_spec, TestClient(ai_main.app), AI_REQUESTS, auth=False)
models_ai, _, _ = render_models(ai_spec["components"]["schemas"], ai_schemas)
(CONTRACT / "ai" / "README.md").write_text(
    fill(CONTRACT / "ai" / "guide.md", VERSION=ai_spec["info"]["version"], REF_TOC=toc_ai, REFERENCE=ref_ai, MODELS=models_ai),
    encoding="utf-8")

# ===================================================================== 3. securitate: backend ↔ app/security
import importlib  # noqa: E402

SEC_MODULES = ["errors", "passwords", "tokens", "lockout", "keys", "signing", "sealing", "validation", "access_log"]
sec_out = []
n_fn = 0
n_prov = 0
for mod_name in SEC_MODULES:
    mod = importlib.import_module(f"app.security.{mod_name}")
    src = inspect.getsource(mod)
    sec_out.append(f"### `security/{mod_name}.py`\n")
    if mod.__doc__:
        sec_out.append(inspect.cleandoc(mod.__doc__) + "\n")
    rows = []
    for name, obj in vars(mod).items():
        if name.startswith("_") or getattr(obj, "__module__", None) != mod.__name__:
            continue
        if inspect.isfunction(obj):
            n_fn += 1
            n_prov += name in getattr(mod, "PROVIZORIU", ())
            sig = str(inspect.signature(obj)).replace("|", "\\|")
            kind = "**async**" if inspect.iscoroutinefunction(obj) else "sync"
            prov = "**da**" if name in getattr(mod, "PROVIZORIU", ()) else "nu"
            doc = inspect.cleandoc(obj.__doc__ or "").replace("\n", " ").replace("|", "\\|")
            rows.append(f"| `{name}{sig}` | {kind} | {prov} | {doc} |")
        elif inspect.isclass(obj):
            doc = inspect.cleandoc(obj.__doc__ or "").replace("\n", " ").replace("|", "\\|")
            fields = ""
            if hasattr(obj, "__dataclass_fields__"):
                fields = " Câmpuri: " + ", ".join(f"`{f}`" for f in obj.__dataclass_fields__)
            rows.append(f"| clasa `{name}` | — | — | {doc}{fields} |")
    import re as _re
    consts = [f"`{n} = {getattr(mod, n)!r}`" for n in vars(mod)
              if n.isupper() and not n.startswith("_") and n != "PROVIZORIU" and _re.search(rf"^{n}\b.*=", src, _re.M)
              and not callable(getattr(mod, n)) and len(repr(getattr(mod, n))) < 80]
    if rows:
        sec_out.append("| Nume și semnătură | Tip | Provizoriu | Ce face |\n|---|---|---|---|")
        sec_out += rows
        sec_out.append("")
    if consts:
        sec_out.append("Constante: " + ", ".join(consts) + "\n")
(CONTRACT / "security" / "README.md").write_text(
    fill(CONTRACT / "security" / "guide.md", N_FUNCTIONS=n_fn, N_PROVISIONAL=n_prov, REFERENCE="\n".join(sec_out)), encoding="utf-8")

# ===================================================================== 4. data: backend ↔ data/
schema_dir = CONTRACT / "data" / "schemas"
schema_dir.mkdir(parents=True, exist_ok=True)
data_rows, data_models = [], {}
for key, (rel, model) in datafiles.FILES.items():
    js = model.model_json_schema()
    js["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    js["title"] = rel
    fname = rel.replace("/", "__").replace(".json", ".schema.json")
    (schema_dir / fname).write_text(json.dumps(js, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    doc = inspect.cleandoc(model.__doc__ or "").split("\n")[0]
    data_rows.append(f"| `data/{rel}` | [{model.__name__}](#{model.__name__.lower()}) | `schemas/{fname}` | {doc} |")
    for n, d in js.get("$defs", {}).items():
        data_models[n] = d
    data_models[model.__name__] = {k: v for k, v in js.items() if k != "$defs"}
models_data, _, _ = render_models(data_models, datafiles)
(CONTRACT / "data" / "README.md").write_text(
    fill(CONTRACT / "data" / "guide.md", FILES_TABLE="\n".join(data_rows), MODELS=models_data), encoding="utf-8")

print(f"ok: API {n_ops} endpoint-uri · AI {n_ai} endpoint-uri · securitate {n_fn} funcții · data {len(datafiles.FILES)} fișiere")
