"""Verificarea de audit a permisiunilor, pe aplicația reală (nu pe un mock):

    uv run --project backend python security/audit/check_endpoints.py

1. Fără token, fiecare endpoint răspunde 401, în afară de cele din PUBLIC.
2. Fiecare cale cu {crew_id}, cerută de un astronaut pentru alt membru al echipajului, răspunde 403.

Folosește cererile de exemplu din scripts/request_examples.py, deci un endpoint nou intră singur în verificare.
Rulează pe o bază de date și pe chei de probă: nu atinge nimic din ce e pe calculator. Iese cu cod de eroare
dacă o regulă e încălcată.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from request_examples import REQUESTS, id_resolver, mock_headers, use_scratch_environment  # noqa: E402

use_scratch_environment()  # înainte de importul aplicației: își citește setările la import

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

API = "/api/v1"
PUBLIC = {
    ("GET", "/health"),
    ("GET", f"{API}/auth/accounts"),         # doar nume, inițiale și rol, pentru ecranul de autentificare
    ("POST", f"{API}/auth/login"),
    ("POST", f"{API}/ingest/measurements"),  # fără token: dovada e semnătura dispozitivului
}
OTHER_ASTRONAUT = "specialist2"   # contul lui cm-2
SOMEONE_ELSE = "cm-1"

client = TestClient(app).__enter__()   # rulează pornirea aplicației: baza de date, conturile, istoricul
real = id_resolver(client)

open_without_token, crew_paths, readable_by_colleague = set(), 0, []
for (method, template), example in REQUESTS.items():
    path, body = real(example.get("path", {})), real(example.get("json"))
    call = {"params": example.get("query"), "json": body}
    allowed = client.request(method, template.format(**path), headers=mock_headers(example["as_"]), **call)
    assert allowed.status_code < 300, f"cererea de exemplu nu mai merge: {method} {template} → {allowed.status_code}"

    if client.request(method, template.format(**path), **call).status_code != 401:
        open_without_token.add((method, template))
    if "{crew_id}" in template:
        crew_paths += 1
        url = template.format(**{**path, "crew_id": SOMEONE_ELSE})
        status = client.request(method, url, headers=mock_headers(OTHER_ASTRONAUT), **call).status_code
        if status != 403:
            readable_by_colleague.append(f"{method} {template} → {status}")

problems = [f"răspunde fără token: {m} {t}" for m, t in sorted(open_without_token - PUBLIC)]
problems += [f"cere token, deși e declarat public: {m} {t}" for m, t in sorted(PUBLIC - open_without_token)]
problems += [f"un astronaut ajunge la datele altuia: {line}" for line in readable_by_colleague]
if problems:
    sys.exit("PICĂ:\n  " + "\n  ".join(problems))
print(f"OK: {len(REQUESTS)} endpoint-uri · {len(REQUESTS) - len(PUBLIC)} cer token (401 fără el) · "
      f"{len(PUBLIC)} publice · {crew_paths} căi cu crew_id, toate 403 pentru alt astronaut")
