# T30 — Reverificarea alertelor

**Cine:** B · **Prioritate:** P2 · **Durată estimată:** ~30 min · **Depinde de:** T17 · **Deblochează:** —

## Ce construiești

La `recheck_at`, SHADOW verifică dacă planul a funcționat: valorile au revenit → alerta se închide singură; nu → urcă un nivel.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/services/alerts.py` (recheck_loop)
- `backend/app/services/pipeline.py`

## Pași

1. Buclă la 5 s (din `lifespan`): alertele deschise cu `recheck_at <= clock.now()`.
2. Rulează regula pilonului pe ziua curentă: fără constatare → `resolved`, istoric `rechecked` + `resolved` („valorile au revenit”); cu constatare → `level + 1` (max 3), `recheck_at` nou, istoric `rechecked`.
3. Evenimente după commit: `alert.updated`.
4. Test: o alertă cu `recheck_at` trecut și valori normale se închide; una cu valori încă mari urcă la nivelul următor.

## Fișierele atinse

- `app/services/alerts.py`
- `app/main.py`
- `tests/routers/test_recheck.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T30 reverificarea alertelor`

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
