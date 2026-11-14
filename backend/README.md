# backend — API-ul SHADOW (FastAPI, uv)

**Cine lucrează aici:** backend (2) + securitate (în `app/security/`)

Acum rulează ca **server mock**: toate endpoint-urile din contract există și răspund, iar textele, mediile,
catalogul și pragurile vin deja din `data/`. Fiecare endpoint se înlocuiește pe rând cu logica reală, fără să i
se schimbe calea, parametrii sau modelul.

```bash
uv sync                                              # instalează exact ce e în uv.lock
uv run uvicorn app.main:app --reload --port 8000     # http://localhost:8000/docs
uv run pytest                                        # testele
uv run ruff format && uv run ruff check --fix        # stilul
```

| Citește | Pentru |
|---|---|
| `PLAN_DE_ATAC_BACKEND.md` (aici) | cum construim: arhitectura, baza de date asincronă, pornirea, testele, planul pe ore |
| `../docs/BACKEND_SARCINI.md` | ce construim: fiecare funcționalitate, cu criteriul „gata când” |
| `../contract/api/README.md` | contractul cu frontend-ul (endpoint-uri, modele, erori, evenimente) |
| `../contract/ai/`, `../contract/security/`, `../contract/data/` | contractele cu serviciul AI, cu securitatea și cu `data/` |

Fișiere care sunt contract (se schimbă doar după regulile din `../contract/README.md`): `app/schemas.py`,
`app/ai_schemas.py`, `app/datafiles.py`, semnăturile din `app/security/`.
