# T11 — Seed: istoricul zilelor 1–96

**Cine:** B · **Prioritate:** P0 · **Durată estimată:** ~45 min · **Depinde de:** T06, T10 · **Deblochează:** T13

## Ce construiești

La pornire, zilele 1–96 ajung în bază: măsurători, check-in-uri, exerciții și sesiunile de tastare, marcate `simulated`.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/db/seed.py` (schelet)
- `backend/app/simulator/scenario.py`
- `handoff/03_BAZA_DE_DATE.md` (measurements, checkins, exercise_sessions, keystroke_sessions)

## Pași

1. `days = await asyncio.to_thread(scenario.generate, data.scenario, from_day=1, to_day=until_day)`.
2. Transformă în obiecte ORM (`Measurement`, `Checkin` cu `source="simulated"`, `ExerciseSession`, `KeystrokeSession` cu `is_baseline=True` pentru primele `keystroke_baseline_duration` zile).
3. Id-uri: `next_id` pentru check-in-uri (`ck`) și exerciții (`ex`); măsurătorile au id întreg automat.
4. `session.add_all(...)` o singură dată, apoi commit (nu rând cu rând).
5. Apelează din `lifespan` după seed-ul conturilor; măsoară durata (țintă: tot `lifespan` sub 10 s).
6. Test: după pornire, cm-2 are 96 de check-in-uri și pulsul de noapte pentru zilele 1–96.

## Fișierele atinse

- `app/db/seed.py`
- `app/main.py`
- `tests/routers/test_seed_history.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] pornirea durează sub 10 s (log-ul spune cât)
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T11 seed: istoricul zilelor 1–96`

## Capcane

- `next_id` de ~600 de ori într-o buclă e lent dacă faci `flush` după fiecare; ține contorul local și scrie `sim_state` o dată la final.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
