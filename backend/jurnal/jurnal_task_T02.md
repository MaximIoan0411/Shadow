## T02 — Ceasul misiunii (SimClock)

**Ce s-a făcut:** `app/clock.py` dă acum timpul misiunii: după `start(...)` pornește în ziua 96 la 07:00 (UTC) și merge de `scale` ori mai repede decât timpul real, măsurat cu `time.monotonic()`. `set_scale` schimbă viteza fără ca ora să sară, `jump_to_day` merge doar înainte, iar `freeze` ține ceasul pe loc (pentru teste). Ziua 1 (`mission_start`) se dă ca parametru, din `data.scenario.start`, nu e scrisă în cod.

**Fișiere modificate:**
- backend/app/clock.py — implementarea completă a `SimClock` (start, now, mission_day, day_start, scale, set_scale, jump_to_day, real_seconds, freeze)
- backend/tests/engine/test_clock.py — nou, 13 teste (cu `time.monotonic` înlocuit în test)

**Teste adăugate:**
- tests/engine/test_clock.py::test_starts_on_day_96_at_0700_utc — după start: 2027-04-15 07:00 UTC, ziua 96
- tests/engine/test_clock.py::test_scale_60_one_real_second_is_one_mission_minute — ×60: 1 s real = 60 s de misiune
- tests/engine/test_clock.py::test_day_start_and_mission_day — ziua 1 = 2027-01-10, ziua 96 = 2027-04-15; trecerea la ziua 2 la miezul nopții
- tests/engine/test_clock.py::test_day_rolls_over_at_midnight — după 17 ore de misiune se trece în ziua 97
- tests/engine/test_clock.py::test_set_scale_does_not_jump — schimbarea vitezei păstrează ora; după aceea merge cu noua viteză
- tests/engine/test_clock.py::test_jump_to_day_forward — salt la ziua 100, 09:30
- tests/engine/test_clock.py::test_jump_to_day_backwards_or_same_raises[96/95/1] — salt înapoi sau în aceeași zi → `ValueError`
- tests/engine/test_clock.py::test_real_seconds — 700 s de misiune la ×60 → 11,67 s reale
- tests/engine/test_clock.py::test_freeze_until_next_start — înghețat stă pe loc; `start()` îl repornește
- tests/engine/test_clock.py::test_invalid_scale_raises — `scale <= 0` → `ValueError`
- tests/engine/test_clock.py::test_not_started_raises — `now()` înainte de `start()` → `RuntimeError`

**Rezultate:** pytest 21 trecute / 0 picate · ruff ok · smoke ok

**Endpointuri devenite reale:** niciunul (ceasul îl folosesc T09 / lifespan-ul mai târziu)

**Texte rămase în română:** niciunul nou (ceasul nu produce texte pentru frontend; mesajele lui de excepție sunt interne, în engleză)

**Decizii luate singur:**
- `now()` înainte de `start()` aruncă `RuntimeError` (o greșeală de pornire se vede imediat, nu se întoarce o oră inventată).
- `scale <= 0` → `ValueError` (altfel `real_seconds` ar împărți la zero).
- `mission_start` fără fus orar → `ValueError` (aceeași regulă ca în `db/base.py`).
- `jump_to_day` cât ceasul e înghețat îl lasă înghețat, dar la noua oră (ca testele cu `freeze` să poată sări zile).
- `grep` găsește `time.time()` / `datetime.now(UTC)` în `app/security/lockout.py` și `tokens.py`: e codul echipei de securitate, care folosește timpul REAL pentru expirarea tokenurilor și blocare (corect). Nu l-am atins.

**Cum verific eu de mână:**
1. `cd backend; uv run pytest tests/engine/test_clock.py -v`
2. `uv run python -c "from datetime import datetime, UTC; from app.clock import clock; clock.start(mission_start=datetime(2027,1,10,tzinfo=UTC), day=96, time_hhmm='07:00', scale=60); print(clock.now(), clock.mission_day())"` → `2027-04-15 07:00:00.0…+00:00 96`

**Mesaj de commit propus:** backend: T02 ceasul misiunii (simclock)

**Următorul task:** T03 (dependențele lui sunt gata: da, T01)
