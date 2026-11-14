# T16 — Drumul unei date + replay la pornire

**Cine:** B · **Prioritate:** P0 · **Durată estimată:** ~75 min · **Depinde de:** T15 · **Deblochează:** T17, T18, T19, T22, T25, T27, T28, T29, T32

## Ce construiești

`services/pipeline.process()` e drumul oricărei date noi: motorul pilonilor afectați → triaj → alerte în bază (cu pașii din catalog și istoricul). La pornire, `replay_history` rulează același drum pe zilele 1–96, deci alerta lui cm-2 o produce motorul.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/services/pipeline.py` (schelet)
- `backend/app/engine/triage.py`, `pillars/immune.py`
- `backend/app/db/models/alerts.py`
- `data/catalog/recommendations.json` (steps, recheck_days)
- `backend/app/services/events.py`

## Pași

1. Hartă `PILLAR_OF_METRIC`: `night_pulse_bpm`, `temperature_c`, `sleep_hours` → immune; tastare/pvt → behavioral; etc. Rulează doar pilonii atinși de `changed`.
2. Încarcă alertele deschise ale membrului (`state != "resolved"`).
3. Pentru `create`: `Alert` cu `next_id("al")`, `state="active"`, `recommendation_id`, pașii din `catalog.steps` (sau propozițiile din `action`), `recheck_at = acum + recheck_days`, istoricul `created`.
4. Pentru `update`/`escalate`: actualizează titlul, explicația, dovezile, `updated_at`; la escaladare `level`, `state="escalated"`, istoric `escalated` cu actorul „SHADOW”.
5. Nivel 3 → pachet spre Pământ: lasă un `# TODO T23` (coada vine mai târziu).
6. Întoarce evenimentele `alert.created` / `alert.updated` / `dashboard.changed` (cu `crew_id`); NU le publica aici.
7. `replay_history`: pentru fiecare zi 1..96, cu ceasul „pus” pe ziua aceea (dă data ca parametru, nu muta ceasul), rulează `process` pe toți membrii; fără evenimente (nimeni nu ascultă la pornire).
8. Apelează `replay_history` în `lifespan` după `seed_history`.
9. Teste: după pornire există o alertă `immune` pentru cm-2 creată în ziua 94 (nivel 1) și escaladată în ziua 95 (nivel 2); niciun alt membru nu are alertă imunitară.

## Fișierele atinse

- `app/services/pipeline.py`
- `app/main.py`
- `tests/routers/test_pipeline_replay.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] pornirea rămâne sub 10 s
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T16 drumul unei date + replay la pornire`

## Capcane

- Încărcarea alertelor cu pașii: `selectinload(Alert.steps), selectinload(Alert.history)`.
- În replay, „acum” e ziua reluată: dă-l ca parametru `day`/`at`, nu folosi `clock.now()`.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
