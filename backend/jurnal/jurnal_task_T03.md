## T03 — Baza de date la pornire

**Ce s-a făcut:** La pornirea serverului, `lifespan` șterge acum baza SQLite veche (fișierul plus `-wal` și `-shm`, doar dacă `RESET_DB_ON_START=true`), creează motorul asincron și toate cele 16 tabele. La oprire închide motorul. `/health` întoarce și câmpul nou `"db": "ok"` după un `SELECT 1`. Endpoint-urile pot cere de acum o sesiune cu `Depends(get_session)`.

**Fișiere modificate:**
- backend/app/main.py — `delete_sqlite_files`, `db_status`, `lifespan` cu ștergere + `init_engine` + `create_all` + `dispose`; câmpul `db` la `/health`
- backend/tests/routers/test_db_startup.py — nou, 4 teste

**Teste adăugate:**
- tests/routers/test_db_startup.py::test_startup_creates_sqlite_file_with_all_tables — după pornire fișierul există și are 16 tabele
- tests/routers/test_db_startup.py::test_health_reports_db_ok — `/health` → `"db": "ok"`
- tests/routers/test_db_startup.py::test_startup_deletes_old_database — o bază veche (cu un tabel `stale`) e ștearsă și recreată
- tests/routers/test_db_startup.py::test_startup_keeps_database_when_reset_is_off — cu `RESET_DB_ON_START=false` baza veche rămâne

**Rezultate:** pytest 25 trecute / 0 picate · ruff ok · smoke ok · serverul pornit de 2 ori la rând: `{"ok":true,"version":"1.2.0","mode":"mock","db":"ok"}` de fiecare dată, fără erori · editorul: fără probleme în fișierele atinse

**Endpointuri devenite reale:** `GET /health` (câmpul `db` verifică baza reală)

**Texte rămase în română:** „**Roluri permise:**” din descrierile Swagger (`app/main.py`, `custom_openapi`) — îl folosește și `scripts/build_docs.py` (în afara `backend/`), deci nu l-am schimbat. Restul: tag-urile din `app/routers/*.py`, mock-ul din `app/examples.py`, textele din `data/`.

**Decizii luate singur:**
- `/health` fără lifespan (cum îl pornește `smoke.py`) întoarce `"db": "unavailable"` în loc să cadă; dacă `SELECT 1` eșuează: `"db": "error"`, cu eroarea în log.
- `delete_sqlite_files` citește calea cu `sqlalchemy.make_url` (nu cu `split("///")` din plan) și nu face nimic pentru baze care nu sunt SQLite sau sunt `:memory:`.
- `lifespan` citește setările din `app.state.settings` (puse de `create_app()` la T01).
- Al patrulea test (`RESET_DB_ON_START=false`) nu era cerut, dar acoperă ramura cealaltă.
- `import app.db.models` e la începutul `main.py` (înregistrează tabelele), cu `noqa: F401` și un comentariu scurt în engleză care explică de ce importul pare nefolosit.
- Câmpul `db` e nou și opțional; `schemas.py` nu se schimbă (`/health` nu are `response_model`).

**Cum verific eu de mână:**
1. `cd backend; uv run uvicorn app.main:app --port 8000` → `curl.exe -s http://localhost:8000/health` → `"db":"ok"`
2. Oprești (Ctrl+C) și pornești din nou → pornește fără eroare, `backend/shadow.sqlite` e recreat
3. `uv run pytest tests/routers/test_db_startup.py -v`

**Mesaj de commit propus:** backend: T03 baza de date la pornire

**Următorul task:** T04 (dependențele lui sunt gata: da, T03)
