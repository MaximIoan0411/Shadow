# T01 — Setările

**Cine:** A · **Prioritate:** P0 · **Durată estimată:** ~15 min · **Depinde de:** T00 · **Deblochează:** T03

## Ce construiești

Toată configurația vine din `app/config.py` (pydantic-settings, din `.env`), iar `create_app()` o folosește.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/config.py` (există)
- `backend/app/main.py`
- `.env.example` din rădăcină

## Pași

1. Citește `Settings` din `app/config.py`; câmpurile există deja.
2. În `create_app()` (`app/main.py`): `settings = get_settings()` la începutul funcției; pune-l în `app.state.settings`.
3. Înlocuiește lista fixă de la CORS cu `settings.cors_origins`.
4. Creează `backend/.env` din exemplu doar local (nu se comite).
5. Scrie testul: cu `monkeypatch.setenv("TIME_SCALE", "7")`, `create_app().state.settings.time_scale == 7`.

## Fișierele atinse

- `app/main.py`
- `tests/test_config.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `grep -rn "os.environ" app/` nu găsește nimic în afară de `datafiles.py`
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T01 setările`

## Nu face

- Nu citi setările la import (`settings = Settings()` la nivel de modul): testele trebuie să le poată schimba.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
