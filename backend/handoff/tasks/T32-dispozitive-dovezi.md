# T32 — Măsurători de la dispozitive, respingeri, dovezi

**Cine:** A · **Prioritate:** P1 · **Durată estimată:** ~60 min · **Depinde de:** T08, T16 · **Deblochează:** —

## Ce construiești

`/ingest/measurements` verifică semnătura și plauzibilitatea, salvează sau respinge; `/security/rejections`, `/evidence/tests` și `/evidence/parameters` lucrează cu date reale.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/routers/security.py` (mock)
- `backend/app/services/security_log.py` (schelet)
- `backend/app/security/signing.py`, `security/validation.py`
- `backend/app/simulator/devices.py` (schelet)

## Pași

1. `ingest`: `signing.verify(obj, signature_b64, keys.device_public.get(device_id))` → altfel `Rejection(kind="bad_signature")`; apoi `validation.check(metric_key, value, repos.recent_device_values(...), limite din checkin_indicators)` → `implausible` / `frozen_sensor`; altfel `Measurement(source="device")` + `pipeline.process`.
2. Respingerea: `Rejection` cu `next_id("rj")`, `measurement.rejected` după commit; răspunsul e tot 200 cu `accepted=False`.
3. `simulator/devices.signed_measurement`: forma `MeasurementIngest`, semnată peste `signing.canonical()`.
4. `GET /security/rejections` din bază, cele mai noi primele.
5. `GET /evidence/tests`: rulează o dată la pornire `pytest tests/engine -q --json-report`-like (sau `pytest --junitxml` într-un fișier temporar, prin `asyncio.create_subprocess_exec`) și ține rezultatul; endpoint-ul îl întoarce.
6. `GET /evidence/parameters`: din `data.params` (mock-ul face deja asta; mută-l în serviciu).
7. Teste: o măsurătoare modificată după semnare → respinsă; 20 de valori identice → `frozen_sensor`; puls 400 → `implausible`.

## Fișierele atinse

- `app/services/security_log.py`
- `app/simulator/devices.py`
- `app/routers/security.py`
- `tests/security/test_ingest.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T32 măsurători de la dispozitive, respingeri, dovezi`

## Capcane

- Până la varianta reală a securității, `signing.verify` acceptă orice semnătură nevidă în afară de `"invalid"`: testele de respingere folosesc `"invalid"`.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
