# T21 — Tablou de bord, panouri, derulator

**Cine:** A · **Prioritate:** P0 · **Durată estimată:** ~75 min · **Depinde de:** T17, T18 · **Deblochează:** —

## Ce construiești

Răspunsurile mari pentru interfață (`dashboard`, panoul pilonului, seria, derulatorul, lista echipajului) se construiesc din bază și din motor, inclusiv pentru o zi trecută (`as_of_day`).

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/routers/crew.py` (mock)
- `backend/app/services/crew.py` (schelet)
- `data/texts/body_functions.json`
- `handoff/02_CONTRACT_ENDPOINTS.md` (T21)
- `contract/api/README.md` §7.2 și §7.8

## Pași

1. `dashboard(crew_id, as_of_day)`: scorurile celor 4 piloni (motorul fiecăruia, pe datele până la ziua cerută), decalajul de percepție (check-in-ul zilei), alerta principală (cea mai gravă deschisă), semnalele încrucișate (gol până la T29), seriile, reamintirile zilei, `radiation_alert_active`, `checkin_done_today`.
2. Pilonii neimplementați încă (Inima, Încărcarea) rămân pe valorile din mock, marcate `data_is_simulated` (le completezi după T27/T28).
3. Panoul: textele din `body_functions.json`, valorile cu baseline-ul (`MetricValue`), graficul pe ultimele 10 zile cu banda și pragul, planul alertei deschise, sursele din `parameters.json`.
4. `series`: `?metric&from_day&to_day` din `repos.series`.
5. `timeline`: starea fiecărui pilon pe fiecare zi până la ziua curentă (din alertele existente pe zile — ieftin; nu rula motorul pe 96 de zile la fiecare cerere).
6. `GET /crew` (cmo): doar starea generală și numărul de alerte.
7. `as_of_day` > ziua curentă → 422 (regula există; păstreaz-o).
8. Teste: cm-2 are zona imunitară `alert`, cm-1 toate `ok`; `as_of_day=93` arată Santinela `ok` pentru cm-2; `timeline` are 96 de zile.

## Fișierele atinse

- `app/services/crew.py`
- `app/routers/crew.py`
- `tests/routers/test_crew_api.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] răspunsul `dashboard` sub ~200 ms local
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T21 tablou de bord, panouri, derulator`

## Capcane

- Nu calcula motorul pe tot istoricul la fiecare cerere; folosește ce e în bază (alerte, măsurători) și calculează doar ziua cerută.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
