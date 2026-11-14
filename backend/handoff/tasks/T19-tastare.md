# T19 — Tastarea

**Cine:** B · **Prioritate:** P0 · **Durată estimată:** ~60 min · **Depinde de:** T16 · **Deblochează:** T20

## Ce construiești

Loturile de apăsări (doar timpi și clasa tastei) se adună într-o sesiune; se calculează trăsăturile, abaterea față de baseline și indicele de oboseală.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/routers/behavioral.py` (mock)
- `backend/app/engine/pillars/behavioral.py` (schelet)
- `backend/app/db/models/measurements.py` (KeystrokeSession: acumulatorii)
- `engine/derived.py` (FLIGHT_PAUSE_MS, KEYSTROKE_*)

## Pași

1. `accumulate`: hold = up − down; flight = down(curent) − down(anterior), sărind pauzele > 2 s; `last_down_ms` leagă loturile; actualizează sume și sume de pătrate; recalculează mediile, deviațiile, `backspace_rate`, `keys_per_min` (din `active_ms`).
2. Baseline-ul tastării: media trăsăturilor sesiunilor cu `is_baseline=True` ale contului; `baseline_ready` după `keystroke_baseline_duration` sesiuni.
3. `fatigue_index`: z-scorurile hold (în sus) și viteză (în jos) cântăresc cel mai mult; 0..100; status după `KEYSTROKE_*`.
4. `POST …/keystrokes/batches` → `KeystrokeResult`; dacă status ≥ watch → `pipeline.process(changed={"keys_per_min"})`.
5. `GET …/keystrokes/summary`: baseline, sesiunea curentă, ultimele `last` sesiuni.
6. Teste: două loturi cu același `session_id` dau aceleași trăsături ca un singur lot cu toate apăsările; o pauză de 5 s nu intră în flight; o sesiune mai lentă cu 20% dă `fatigue_index` vizibil mai mare.

## Fișierele atinse

- `app/engine/pillars/behavioral.py`
- `app/services/behavioral.py`
- `app/routers/behavioral.py`
- `tests/engine/test_keystrokes.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] în bază nu există niciun caracter tastat (doar numere)
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T19 tastarea`

## Nu face

- Nu adăuga un câmp pentru caracter: modelul `KeyEvent` îl respinge intenționat.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
