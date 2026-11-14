# backend — API-ul SHADOW (FastAPI, uv)

**Cine lucrează aici:** backend (2) + securitate (în `app/security/`)

Serverul real: toate endpoint-urile din contract lucrează cu baza de date, motorul de triaj, coada spre Pământ și
codul de securitate din `app/security/` (semnături Ed25519, pachete AES-256-GCM, tokenuri HS256, parole argon2id,
jurnal de acces cu lanț de hash-uri). Textele, mediile, catalogul și pragurile vin din `data/`.

```bash
uv sync                                              # instalează exact ce e în uv.lock
uv run uvicorn app.main:app --reload --port 8000     # http://localhost:8000/docs
uv run pytest                                        # testele
uv run ruff format && uv run ruff check --fix        # stilul
```

## Setări și chei

Pornește fără nicio pregătire. Setările se pot schimba dintr-un `.env` (în rădăcina repo-ului sau aici), după
modelul `../.env.example`.

| Ce | Cum |
|---|---|
| cheile (navă, Pământ, dispozitive, legătură) | la prima pornire, cele care lipsesc sunt create în `../security/keys/keys_files/` (nu intră în git); o cheie existentă nu e înlocuită niciodată |
| secretul tokenurilor | `JWT_SECRET`, minimum 32 de caractere; lăsat gol, se alege unul aleator la fiecare pornire |
| tokenurile `mock-<utilizator>` | oprite; doar testele le pornesc (`ALLOW_MOCK_TOKENS=true`). Cu ele se intră FĂRĂ parolă |
| medicul AI | serviciul din `../ai/`, la `AI_URL` (implicit `http://127.0.0.1:8001`); dacă nu răspunde în `AI_TIMEOUT_S`, răspunsul e textul din catalog |

| Citește | Pentru |
|---|---|
| `PLAN_DE_ATAC_BACKEND.md` (aici) | cum construim: arhitectura, baza de date asincronă, pornirea, testele, planul pe ore |
| `../docs/BACKEND_SARCINI.md` | ce construim: fiecare funcționalitate, cu criteriul „gata când” |
| `../contract/api/README.md` | contractul cu frontend-ul (endpoint-uri, modele, erori, evenimente) |
| `../contract/ai/`, `../contract/security/`, `../contract/data/` | contractele cu serviciul AI, cu securitatea și cu `data/` |

Fișiere care sunt contract (se schimbă doar după regulile din `../contract/README.md`): `app/schemas.py`,
`app/ai_schemas.py`, `app/datafiles.py`, semnăturile din `app/security/`.
