# T10 — Simulatorul: generatorul de scenariu

**Cine:** B · **Prioritate:** P0 · **Durată estimată:** ~75 min · **Depinde de:** T05 · **Deblochează:** T11

## Ce construiești

`simulator/scenario.generate()` produce, PUR (fără bază), datele zilelor cerute pentru toți membrii, după `data/scenario/scenario.json`, la fel la fiecare rulare.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/simulator/scenario.py` (schelet)
- `data/scenario/scenario.json`
- `backend/app/datafiles.py` (ScenarioFile)
- `docs/BACKEND_SARCINI.md` §4 (tabelul evenimentelor)

## Pași

1. Pentru fiecare zi și membru: `rng = random.Random(scenario.seed * 1000 + day * 10 + nr_membru)` (determinist pe zi, nu pe interval).
2. Valori zilnice din `crew_baselines[crew]` + zgomot mic: `night_pulse_bpm` (03:00, zgomot ≤ `noise_max_bpm` = 0,8), `resting_pulse_bpm`, `hrv_lnrmssd`, `temperature_c`, `sleep_hours`, `systolic/diastolic_mmhg`, `glucose_mg_dl`.
3. Check-in zilnic la 07:00 (dispoziția 4 de obicei, cu mici variații) cu valorile manuale.
4. Exerciții: 2 sesiuni de rezistență (09:00 și 16:00) în zilele normale.
5. O sesiune de tastare pe zi (07:15) cu trăsăturile din baseline (`keys_per_min`, `hold_ms_mean`) — pentru baseline-ul tastării.
6. Aplică evenimentele: `poor_sleep` (somn −1,6 h, tastare −10% pentru toți), `skipped_exercise` (0 sesiuni), `infection_onset` (pulsul de noapte + `night_pulse_bpm_delta_by_day`, temperatură +0,4, somn −1,1), `keystroke_slowdown` (tastare −18%, hold +17%, dispoziția 4), `cardio_deconditioning` (puls de repaus în sus, HRV în jos).
7. `solar_storm` NU se generează aici (e live, T25).
8. Teste în `tests/engine/test_scenario.py`: două rulări dau exact aceleași date; `generate(…, 94, 94)` == ziua 94 din `generate(…, 1, 96)`; pulsul de noapte al lui cm-2: ziua 93 < baseline+3, ziua 94 ≥ baseline+4, ziua 95 ≥ baseline+4; ziua 61 nu are exerciții pentru cm-2.

## Fișierele atinse

- `app/simulator/scenario.py`
- `tests/engine/test_scenario.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T10 simulatorul: generatorul de scenariu`

## Nu face

- Nu scrie în bază aici (e T11).
- Nu scrie evenimentele în cod: vin din `scenario.events`.

## Capcane

- Zgomotul mare ar muta zilele alertei. Păstrează zgomotul pulsului de noapte sub 0,8 bpm.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
