# T13 — Interogările refolosite (repos)

**Cine:** B · **Prioritate:** P0 · **Durată estimată:** ~30 min · **Depinde de:** T11 · **Deblochează:** T14

## Ce construiești

`db/repos.py` dă seriile pe zile pentru motor și pentru grafice, ca tipuri `Point`, fără ca motorul să știe de SQLAlchemy.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/db/repos.py` (schelet)
- `backend/app/engine/types.py` (Point)
- `handoff/03_BAZA_DE_DATE.md` (measurements, indexul ix_meas_crew_metric_day)

## Pași

1. `series`: `select(Measurement).where(crew_id, metric_key, mission_day between).order_by(mission_day, measured_at)`; păstrează ultima valoare pe zi.
2. Metricile din check-in (`temperature_c`, `sleep_hours`, `systolic_mmhg`…) vin din `checkins` dacă nu sunt în `measurements`: tratează-le printr-o hartă `CHECKIN_METRICS`.
3. `series_all_crew`, `latest`, `recent_device_values` după aceeași idee.
4. Teste: `series(cm-2, night_pulse_bpm, 90, 96)` are 7 puncte crescătoare; o metrică de check-in merge la fel.

## Fișierele atinse

- `app/db/repos.py`
- `tests/routers/test_repos.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T13 interogările refolosite (repos)`

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
