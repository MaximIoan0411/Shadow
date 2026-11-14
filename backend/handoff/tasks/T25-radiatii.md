# T25 — Radiații: generator, detector, adăpost

**Cine:** B · **Prioritate:** P1 · **Durată estimată:** ~60 min · **Depinde de:** T16 · **Deblochează:** T26

## Ce construiești

Dozimetrul simulat dă rata dozei; la furtună rata urcă, detectorul dă alerta de nivel 1 după 3 citiri peste 2 × media pe 24 h, iar „Sunt în adăpost” aplică ecranarea.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/simulator/radiation.py`, `engine/radiation.py`, `simulator/live.py` (schelet)
- `backend/app/routers/radiation.py`, `routers/demo.py` (sep/start, sep/stop)
- `data/parameters.json`: `prag_alerta_sep_rata_vs_baseline`, `reducere_doza_adapost_capsula`
- `data/donki/donki_sep_event.json`
- `engine/derived.py` (SEP_CONSECUTIVE_READINGS)

## Pași

1. `simulator/radiation.dose_rate`: fond din mediu (`baseline_dose_usv_h`) + zgomot ±5%; după onset: urcă în ~20 min la `peak_multiplier` (6) × fond, scade exponențial în ore; × `shield_factor` (0,3) în adăpost.
2. `engine/radiation`: `mean_24h`, `is_alert` (ultimele 3 ≥ 2 × medie).
3. `POST /sim/sep/start`: `sim_state["storm"] = {event_id, onset_at = acum + starts_in_min}`; `stop`: șterge starea → `radiation.cleared`.
4. `live_simulator` (pas 2 s, din `lifespan`): cât e furtună, o citire nouă (`RadiationReading`) la fiecare pas; la alertă → `Finding(radiation, level 1, "radiation-1-1")` prin pipeline, `onboard_alert_at`, `radiation.alert`; `radiation.reading` cel mult la 2 s.
5. `POST /radiation/shelter-ack`: `sheltered_since`; `GET /radiation/status` (cu `profile_is_synthetic=True`), `GET /radiation/series`.
6. Teste (ceas mutat manual): 2 citiri peste prag → fără alertă; a 3-a → alertă; în adăpost rata scade.

## Fișierele atinse

- `app/simulator/radiation.py`
- `app/engine/radiation.py`
- `app/simulator/live.py`
- `app/services/radiation.py`
- `app/routers/radiation.py`
- `app/routers/demo.py`
- `tests/engine/test_radiation.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `test_sep_alert_at_2x_mean` există
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T25 radiații: generator, detector, adăpost`

## Nu face

- Nu inventa doza măsurată pentru evenimentul din 2024: nu e publicată; curba e sintetică și marcată așa.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
