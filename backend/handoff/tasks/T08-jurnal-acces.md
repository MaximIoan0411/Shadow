# T08 — Jurnalul de acces

**Cine:** A · **Prioritate:** P1 · **Durată estimată:** ~30 min · **Depinde de:** T07 · **Deblochează:** T32

## Ce construiești

Accesurile importante lasă urmă în `access_log`, iar `GET /access-log` le citește din bază.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/security/access_log.py`
- `backend/app/deps.py` (crew_access)
- `backend/app/routers/security.py` (access_log)
- `backend/app/services/access.py` (schelet)

## Pași

1. În `crew_access`: dacă un `cmo` citește datele altui membru → `access_log.write(action="read_dashboard" sau după cale, outcome="allowed")`; orice 403 → `outcome="denied"`, `action="access_denied"`.
2. În `GET /alerts/{id}` citit de `cmo` → `read_alert`.
3. `GET /access-log`: astronautul vede doar intrările cu `crew_id` al lui; `cmo` tot; cele mai noi primele; `limit`.
4. Notă: până la varianta reală a securității, `access_log.write` ține totul în memorie; dacă vrei să-l vezi în bază, cere echipei de securitate varianta cu `INSERT` (semnătura e aceeași).
5. Test: comandantul cere `/crew/cm-2/dashboard` → 403 și o intrare `denied` în jurnal; `medic` citește → intrare `allowed`.

## Fișierele atinse

- `app/deps.py`
- `app/routers/security.py`
- `app/services/access.py`
- `tests/security/test_access_log_wiring.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T08 jurnalul de acces`

## Nu face

- Nu scrie parole sau tokenuri în jurnal.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
