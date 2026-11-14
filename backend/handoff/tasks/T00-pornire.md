# T00 — Pornire și verificare

**Cine:** A+B · **Prioritate:** P0 · **Durată estimată:** ~15 min · **Depinde de:** — · **Deblochează:** T01, T02

## Ce construiești

Ambii aveți repo-ul pornit local, mock-ul răspunde și toate verificările trec, înainte să scrieți cod.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/README.md`
- `backend/handoff/04_SCHELET.md`

## Pași

1. Clonează repo-ul și instalează `uv` (https://docs.astral.sh/uv/).
2. `cd backend && uv sync`.
3. `uv run uvicorn app.main:app --reload --port 8000` și deschide http://localhost:8000/docs.
4. Autentifică-te în Swagger: `POST /api/v1/auth/login` cu `specialist2` / `cm2-shadow`; apoi „Authorize” cu tokenul primit.
5. Apelează `GET /api/v1/crew/cm-2/dashboard`: vezi alerta imunitară din scenariu.
6. Rulează testele și verificarea contractului (comenzile de mai jos).
7. Citește `04_SCHELET.md`: vezi ce e gata, ce e mock și ce e schelet.

## Fișierele atinse

- nimic de schimbat

## Gata când

- [ ] `uv run pytest -q` → 5 teste trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] Swagger se deschide și login-ul merge
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T00 pornire și verificare`

## Nu face

- Nu șterge `app/examples.py`: mock-ul trebuie să meargă până la T34.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
