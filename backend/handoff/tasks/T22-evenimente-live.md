# T22 — Evenimentele live

**Cine:** A · **Prioritate:** P0 · **Durată estimată:** ~30 min · **Depinde de:** T16 · **Deblochează:** —

## Ce construiești

`/events` trimite `mission.tick` din ceasul real al misiunii la o secundă, `: ping` la 15 secunde, iar toate serviciile publică doar după commit.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/routers/events.py`
- `backend/app/deps.py` (publish, subscribe)
- `backend/app/services/mission.py` (mission_ticker)
- `backend/app/services/events.py`

## Pași

1. `mission_ticker`: buclă cu `await asyncio.sleep(1)`; `publish("mission.tick", {"sim_now": clock.now(), "mission_day": …})`; pornit din `lifespan`, anulat la oprire.
2. În `routers/events.py`: scoate tick-ul fals din generator; la 15 s fără evenimente trimite comentariul `: ping\n\n`.
3. `deps.publish`: `at` = `clock.now()`.
4. Verifică toate serviciile scrise până acum: publică **după** commit (`publish_all`).
5. Test: abonează un client, publică un eveniment cu `crew_id="cm-1"`; contul `specialist2` nu-l primește, `medic` da.

## Fișierele atinse

- `app/services/mission.py`
- `app/routers/events.py`
- `app/main.py`
- `tests/routers/test_events.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `curl -N -H 'Authorization: Bearer mock-specialist2' localhost:8000/api/v1/events` arată un tick pe secundă
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T22 evenimentele live`

## Capcane

- Un `asyncio.Queue` pe abonat (există); nu bloca bucla cu operații lente în generator.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
