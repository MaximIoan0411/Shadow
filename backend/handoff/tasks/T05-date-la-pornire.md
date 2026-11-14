# T05 — Datele din data/ la pornire

**Cine:** B · **Prioritate:** P0 · **Durată estimată:** ~20 min · **Depinde de:** T03 · **Deblochează:** T09, T10, T12

## Ce construiești

La pornire, `load_all()` încarcă și validează tot `data/`; rezultatul stă în `app.state.data`, iar serviciile îl primesc printr-o dependență.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/datafiles.py` (gata)
- `contract/data/README.md`
- `backend/app/engine/types.py`, `engine/derived.py` (gata)

## Pași

1. În `lifespan`, după baza de date: `app.state.data = load_all(settings.data_dir)` (relativ la `backend/`).
2. În `app/deps.py`: `def get_data(request: Request) -> DataBundle: return request.app.state.data`.
3. Adaugă `app.state.keys = security.keys.load_keys(link_aes_key_b64=settings.link_aes_key_b64)`.
4. Test: `DATA_DIR` spre un folder gol → pornirea aplicației aruncă `DataError` cu lista fișierelor lipsă.
5. Test: `get_data` întoarce `params.value("nightsignal_red_delta_bpm") == 4`.

## Fișierele atinse

- `app/main.py`
- `app/deps.py`
- `tests/routers/test_data_startup.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `uv run --project backend python scripts/validate_data.py` → OK
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T05 datele din data/ la pornire`

## Nu face

- Nu copia pragurile în cod: se citesc din `params`.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
