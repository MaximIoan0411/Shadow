# T09 — Misiunea și mediile

**Cine:** A · **Prioritate:** P0 · **Durată estimată:** ~40 min · **Depinde de:** T02, T05 · **Deblochează:** —

## Ce construiești

`/mission`, `/environments`, `PUT /mission/environment` și `PUT /sim/clock` (doar viteza) folosesc ceasul și `data/environments.json`; mediul curent stă în `sim_state`.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/routers/mission.py`
- `backend/app/services/mission.py` (schelet)
- `data/environments.json`
- `handoff/02_CONTRACT_ENDPOINTS.md` (T09)

## Pași

1. La pornire (lifespan): `clock.start(mission_start=data.scenario.start, day=data.scenario.start_day, time_hhmm=data.scenario.start_time, scale=settings.time_scale)` și `sim_state["environment"] = {"id": data.environments.default}`.
2. `services/mission.state(session, data)` → `MissionState`: `sim_now = clock.now()`, `mission_day`, `total_days`, `time_scale`, mediul curent (`EnvironmentInfo` din fișier), `LinkStatus` (întârzierea și `one_way_delay_real_s = clock.real_seconds(...)`; `queued_down`/`queued_up` = numărul pachetelor `queued` din bază).
3. `PUT /mission/environment`: scrie în `sim_state`; întoarce noul `MissionState`; evenimentul `environment.changed` după commit.
4. `PUT /sim/clock`: `time_scale` → `clock.set_scale`; `mission_day` rămâne mock până la T33 (dar regula 409 înapoi rămâne).
5. Teste: `/mission` dă ziua 96; după `PUT environment iss`, `link.one_way_delay_s == 1`; `time_scale` se schimbă fără să sară ora.

## Fișierele atinse

- `app/services/mission.py`
- `app/routers/mission.py`
- `app/main.py`
- `tests/routers/test_mission.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T09 misiunea și mediile`

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
