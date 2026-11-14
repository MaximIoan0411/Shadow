# T02 — Ceasul misiunii (SimClock)

**Cine:** A · **Prioritate:** P0 · **Durată estimată:** ~30 min · **Depinde de:** T00 · **Deblochează:** T09

## Ce construiești

`app/clock.py` dă timpul misiunii: pornește în ziua 96 la 07:00 și merge de `scale` ori mai repede decât timpul real.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/clock.py` (schelet)
- `data/scenario/scenario.json` (start, start_day, start_time)

## Pași

1. Implementează `SimClock` cu trei câmpuri interne: `_real0` (`time.monotonic()` la pornire), `_sim0` (data misiunii la pornire), `_scale`.
2. `now() = _sim0 + timedelta(seconds=(monotonic() - _real0) * _scale)`, cu `tzinfo=UTC`.
3. `mission_day(at)` = `(at - mission_start).days + 1`; `day_start(day)` = `mission_start + (day - 1) zile`.
4. `start(mission_start, day, time_hhmm, scale)`: `_sim0 = day_start(day) + ora`.
5. `set_scale`: fixează `_sim0 = now()`, `_real0 = monotonic()`, apoi schimbă viteza (ora nu sare).
6. `jump_to_day(day)`: `ValueError` dacă `day <= mission_day()`; altfel mută `_sim0` la ziua aceea.
7. `real_seconds(s) = s / scale`; `freeze(at)`: `now()` întoarce `at` până la următorul `start`.
8. Teste în `tests/engine/test_clock.py`: ziua 96 la pornire; ×60 → 1 s real = 60 s de misiune (cu `freeze` sau monkeypatch pe `time.monotonic`); `set_scale` nu sare; `jump_to_day` înapoi dă `ValueError`.

## Fișierele atinse

- `app/clock.py`
- `tests/engine/test_clock.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `grep -rn "datetime.now\|datetime.utcnow" app/` nu găsește nimic în codul nou
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T02 ceasul misiunii (simclock)`

## Nu face

- Nu folosi `time.time()` (se poate schimba); folosește `time.monotonic()`.

## Capcane

- `mission_start` vine din `data.scenario.start` (2027-01-10T00:00Z), nu din cod.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
