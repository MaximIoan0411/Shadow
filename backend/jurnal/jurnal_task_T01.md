## T01 — Setările

**Ce s-a făcut:** `create_app()` citește acum setările cu `get_settings()` (la apel, nu la import) și le pune în `app.state.settings`. Lista CORS nu mai e scrisă în cod: vine din `settings.cors_origins`, deci din `.env` / mediu (`CORS_ORIGINS`). Textele din `main.py` care ajung la frontend sunt acum în engleză (mesajele de eroare 422 și 500, descrierea API-ului și endpoint-ul `/health` din Swagger). Am creat local `backend/.env` din `.env.example`; fișierul e ignorat de git.

**Fișiere modificate:**
- backend/app/main.py — `settings = get_settings()` în `create_app()`, `app.state.settings`, CORS din setări, texte traduse în engleză, formatat cu ruff
- backend/tests/test_config.py — nou, 3 teste
- backend/.env — creat doar local (ignorat de git, nu se comite)

**Teste adăugate:**
- tests/test_config.py::test_settings_read_from_env_at_create_app — `TIME_SCALE=7` în mediu → `app.state.settings.time_scale == 7`
- tests/test_config.py::test_cors_origins_come_from_settings — `CORS_ORIGINS` din mediu ajunge în setări și în middleware-ul CORS
- tests/test_config.py::test_validation_error_message_is_english — eroarea 422 are codul `validation_error` și mesajul în engleză

**Rezultate:** pytest 8 trecute / 0 picate · ruff ok · smoke ok · `git grep os.environ -- app` → doar `app/datafiles.py:297`

**Endpointuri devenite reale:** niciunul (s-au tradus doar texte în erorile comune și la `/health`)

**Texte rămase în română:** tag-urile Swagger din celelalte routere (`app/routers/*.py`, de exemplu „1. Autentificare”), toate răspunsurile mock din `app/examples.py` și textele din `data/`. Le traduc taskurile care ating acele fișiere.

**Decizii luate singur:**
- În `backend/.env` am pus `CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]`, nu doar `localhost:3000` ca în `.env.example`, ca să rămână exact lista care era scrisă în cod. `.env.example` (rădăcina) nu l-am atins.
- Am tradus și textele din Swagger din `main.py` (descrierea API-ului, tag-ul și sumarul de la `/health`), conform regulii „textele din fișierele modificate se traduc”. `smoke.py` compară doar metodele și căile, deci nu e afectat.
- Am rulat `ruff format` doar pe `app/main.py` și `tests/test_config.py`, nu pe tot `backend/`.
- Am adăugat un al treilea test (mesajul 422 în engleză), care acoperă traducerea.
- Notă: în `git diff` apare și ștergerea `backend/JURNAL.md`, mutat în `backend/jurnal/jurnal_task_T00.md` la cererea ta.

**Cum verific eu de mână:**
1. `cd backend; uv run uvicorn app.main:app --reload --port 8000`
2. `curl.exe -i -X OPTIONS http://localhost:8000/api/v1/auth/login -H "Origin: http://127.0.0.1:3000" -H "Access-Control-Request-Method: POST"` → `access-control-allow-origin: http://127.0.0.1:3000`
3. `curl.exe -s -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d "{}"` → `"message":"The submitted data does not match the contract."`

**Mesaj de commit propus:** backend: T01 setările

**Următorul task:** T02 (dependențele lui sunt gata: da)
