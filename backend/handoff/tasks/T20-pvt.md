# T20 — Testul de reacție (PVT-B)

**Cine:** B · **Prioritate:** P1 · **Durată estimată:** ~30 min · **Depinde de:** T19 · **Deblochează:** —

## Ce construiești

Rezultatul testului de 3 minute: viteza medie (1/RT), lapsusurile (RT ≥ 355 ms), abaterea față de baseline, cu primele teste ca antrenament.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/engine/pillars/behavioral.py` (pvt_summary, pvt_finding)
- `data/parameters.json`: `pvtb_lapse_threshold`, `pvt_reliable_change_derived`, `pvt_practice_runs`

## Pași

1. `pvt_summary`: ignoră încercările cu `false_start` din RT; `rt_ms = null` = lapsus; `mean_speed = media(1000 / rt_ms)`.
2. Primele `pvt_practice_runs[1]` (3) teste ale contului: `is_practice=True`, fără baseline și fără alertă.
3. `deviation_sd = (speed − base_speed) / base_sd`; ≤ −1,24 → `watch` și un `Finding` behavioral nivel 1 (`behavioral-1-1`).
4. `POST …/pvt` salvează și întoarce `PvtResult`; `GET …/pvt` istoricul.
5. Teste: lapsus la 355 ms exact; un test lent după 5 teste normale dă `watch`.

## Fișierele atinse

- `app/engine/pillars/behavioral.py`
- `app/services/behavioral.py`
- `app/routers/behavioral.py`
- `tests/engine/test_pvt.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T20 testul de reacție (pvt-b)`

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
