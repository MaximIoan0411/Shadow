# 01 — Contextul proiectului (de dat lui Claude la fiecare task)

## Proiectul

**SHADOW** — NASA Space Apps 2026, challenge „Create Health Monitoring Software for Astronauts on Space Missions”.
Prototip de sprijin pentru decizie, **nu dispozitiv medical**. Hackathon de 24 de ore.

Ideea centrală: **decalajul de percepție** — astronautul spune „sunt bine”, dar datele lui obiective arată altceva.
Fiecare astronaut e comparat **cu el însuși** (baseline personal din zbor), nu cu valori clinice generale.

Patru piloni: **Tastatura** (comportamental: ritmul tastării, test de reacție), **Inima** (cardiovascular),
**Santinela** (imunitar: puls de noapte, regula NightSignal), **Încărcarea** (oase și mușchi: exerciții).
Plus radiațiile (furtuna solară reală din NASA DONKI, 11 mai 2024).

Triaj pe 3 niveluri: **1** astronautul singur, **2** ofițerul medical de la bord, **3** Pământul — prin o coadă cu
întârzierea reală a legăturii (Marte: 3–22 min; în demo 700 s, accelerat ×60), cu pachete semnate și criptate.

Misiunea are 140 de zile și **pornește în ziua 96, la 07:00**: zilele 1–95 sunt istoric generat la pornirea
serverului. Echipaj: `cm-1` Comandant, `cm-2` Specialist de misiune 2 (are evenimentele din scenariu), `cm-3`
Ofițer medical de bord (rol `cmo`), `cm-4` Inginer de zbor. Plus contul `earth` (medicul de pe Pământ).
**Fiecare astronaut are contul lui.**

## Stack

Python 3.12 · uv · FastAPI · Pydantic v2 · pydantic-settings · SQLAlchemy 2.0 **asincron** + aiosqlite ·
SQLite (fișier, WAL, recreat la fiecare pornire, **fără migrări**) · pytest + pytest-asyncio + httpx · ruff.

## Structura (ce poți importa de unde)

```
routers/     subțiri: citesc cererea, verifică rolul, apelează un serviciu, întorc un model din schemas.py
services/    logica: tranzacții, ordinea pașilor, scrieri, evenimente (întoarse ca listă, publicate după commit)
engine/      funcții PURE: fără bază, fără HTTP, fără ceas; pragurile vin ca parametru
db/          modelele (db/models/*), sesiunea (db/session.py), interogările (db/repos.py), seed-ul
simulator/   datele generate; link/  coada navă ↔ Pământ; security/  al echipei de securitate (doar îl apelezi)
```

| Stratul | Poate importa | NU poate importa |
|---|---|---|
| `routers/` | `services/`, `schemas`, `deps` | `db/models` direct, `engine/` |
| `services/` | `engine/`, `db/`, `security/`, `clock`, `services/events` | `routers/` |
| `engine/` | biblioteca standard, `engine/types.py`, `engine/derived.py` | `db/`, `fastapi`, `clock`, `security/` |
| `db/` | `sqlalchemy`, `config`, `engine/types.py` (doar în repos) | restul |

## Fișiere care sunt CONTRACT (nu le schimba fără acordul echipei)

- `app/schemas.py` — modelele API (frontend-ul depinde de ele). Doar câmpuri **opționale** noi fără anunț.
- Semnăturile routerelor (cale, parametri, `response_model`, coduri de eroare).
- `app/ai_schemas.py` — contractul cu serviciul AI (copie a `ai/service/schemas.py`).
- `app/datafiles.py` — formatul fișierelor din `data/`.
- Semnăturile din `app/security/` — le scrie echipa de securitate; tu doar le apelezi.

## Reguli pentru cod asincron (obligatorii)

1. Orice funcție care atinge baza e `async def` și face `await session.execute(...)`.
2. O sesiune pe cerere (`Depends(get_session)`); task-urile din fundal își deschid **propria** sesiune:
   `from app.db import session as db` apoi `async with db.SessionLocal() as s:` (importă **modulul**, nu numele).
3. Relațiile au `lazy="raise"`: încarcă-le cu `select(Alert).options(selectinload(Alert.steps))`.
4. `expire_on_commit=False` (deja setat): obiectele se pot citi după commit.
5. Nimic blocant în `async def` (fără `time.sleep`, `requests`). Lucru greu pe procesor:
   `await asyncio.to_thread(funcție, ...)` — hash-ul parolelor, generarea istoricului, rularea motorului pe istoric.
6. Tranzacții scurte: SQLite are un singur scriitor. Nu ține o tranzacție deschisă în timpul unui apel HTTP.
7. **Evenimentele se publică DUPĂ `commit()`** (`services/events.publish_all`).
8. **Timpul doar din `clock.now()`** (timpul misiunii). Niciodată `datetime.now()`. Datele-oră au fus orar (UTC).
9. Inserări: `crew` întâi, apoi `await session.flush()`, apoi restul (fără relații ORM, ordinea nu e garantată).

## Convenții

- Cod în engleză; **textele pentru utilizator în română**, complete, gata de afișat (titluri, explicații, erori).
- Erori: `raise ApiError(status, code, mesaj, details)` din `app/deps.py`. Coduri fixe: `unauthorized`,
  `invalid_credentials`, `forbidden`, `not_found`, `invalid_state`, `validation_error`, `too_many_attempts`.
- Id-uri: `await next_id(session, "al")` → `"al-0001"` (`app/ids.py`).
- Pragurile: din `app.state.data.params.value("<id>")` (`data/parameters.json`); cele alese de echipă stau doar în
  `engine/derived.py`. Recomandările: `app.state.data.catalog` (`data/catalog/recommendations.json`).
- Log-uri: `logging.getLogger(__name__)`; niciodată parole, tokenuri sau conținutul pachetelor.
- Funcții mici; un router peste ~15 rânduri înseamnă logică de mutat într-un serviciu.

## Comenzi

```bash
cd backend
uv sync                                             # dependențele
uv run uvicorn app.main:app --reload --port 8000    # pornește (baza se recreează)
uv run pytest -q                                    # testele
uv run ruff format && uv run ruff check --fix       # stilul
cd .. && uv run --project backend python scripts/smoke.py   # contractul (TREBUIE să treacă înainte de PR)
```

Testele folosesc fixture-ul din `backend/tests/conftest.py` (bază într-un **fișier** temporar, nu în memorie:
în memorie, scrierile în paralel se pierd fără eroare) și `auth("specialist2")` pentru antet.

Documente complete, dacă ai nevoie: `backend/PLAN_DE_ATAC_BACKEND.md`, `docs/BACKEND_SARCINI.md`,
`contract/api/README.md`.
