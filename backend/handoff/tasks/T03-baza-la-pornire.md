# T03 — Baza de date la pornire

**Cine:** A · **Prioritate:** P0 · **Durată estimată:** ~30 min · **Depinde de:** T01 · **Deblochează:** T04, T05, T06

## Ce construiești

La pornire, `lifespan` șterge baza veche, creează motorul și toate tabelele; endpoint-urile pot cere o sesiune cu `Depends(get_session)`.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/main.py` (lifespan)
- `backend/app/db/session.py` (gata)
- `backend/app/db/models/` (gata)
- `handoff/03_BAZA_DE_DATE.md`

## Pași

1. În `lifespan`: dacă `settings.reset_db_on_start`, șterge fișierul SQLite și `-wal`, `-shm` (funcția `delete_sqlite_files` e în plan, secțiunea 6).
2. `engine = db.init_engine(settings.database_url)`; `import app.db.models` (înregistrează tabelele); `await conn.run_sync(Base.metadata.create_all)`.
3. La oprire: `await engine.dispose()`.
4. `/health`: întoarce și `"db": "ok"` după un `SELECT 1` (câmp nou, opțional — contractul permite).
5. Test: după pornirea aplicației (fixture-ul `client`), fișierul SQLite există și are 16 tabele (`sqlalchemy.inspect`).

## Fișierele atinse

- `app/main.py`
- `tests/routers/test_db_startup.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `uv run uvicorn app.main:app` pornește de două ori la rând fără eroare (baza se recreează)
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T03 baza de date la pornire`

## Nu face

- Nu adăuga Alembic.
- Nu importa `SessionLocal` direct (`from app.db.session import SessionLocal` dă `None`).

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
