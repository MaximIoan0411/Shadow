# scripts — unelte

**Cine lucrează aici:** oricine

Toate se rulează din rădăcina repo-ului, cu mediul backend-ului (importă codul lui):

| Comandă | Ce face |
|---|---|
| `uv run --project backend python scripts/smoke.py` | verifică toate contractele: endpoint-uri, permisiuni, date, contractul AI, semnăturile de securitate. **Înainte de fiecare PR.** |
| `uv run --project backend python scripts/build_docs.py` | regenerează tot `contract/` (OpenAPI, JSON Schema, README-uri) |
| `uv run --project backend python scripts/validate_data.py` | verifică doar fișierele din `data/` |
| `bash scripts/gen_types.sh` | regenerează `frontend/src/lib/shadow-api.d.ts` din `contract/api/openapi.json` |

`request_examples.py` are câte o cerere de exemplu pentru fiecare endpoint (API și AI). Un endpoint nou fără
exemplu face `smoke.py` să pice.
