# T12 — Motor: baseline-ul personal

**Cine:** B · **Prioritate:** P0 · **Durată estimată:** ~30 min · **Depinde de:** T05 · **Deblochează:** T14

## Ce construiești

`engine/baseline.compute()` calculează normalul personal (mediana + deviația robustă) dintr-o serie, fără zilele în alertă.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/engine/baseline.py` (schelet)
- `backend/app/engine/types.py`
- `backend/app/engine/derived.py` (MIN_SPREAD)

## Pași

1. Filtrează punctele: fără `exclude_days`; doar ultimele `window_days` (dacă e dat).
2. `median` = mediana valorilor; `spread = max(1.4826 × MAD, min_spread)`; `n`; `ready = n >= min_n`.
3. Serie goală → `Baseline(median=nan, spread=min_spread, n=0, ready=False)`.
4. `deviation(value, base) = (value - base.median) / base.spread`.
5. Teste în `tests/engine/test_baseline.py`: valori constante → spread = min_spread; un vârf izolat nu mută mediana; zilele excluse nu contează; `ready` la `min_n`.

## Fișierele atinse

- `app/engine/baseline.py`
- `tests/engine/test_baseline.py` (nou)

## Gata când

- [ ] `uv run pytest tests/engine -q`
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T12 motor: baseline-ul personal`

## Nu face

- Nu importa nimic din `db/` sau `fastapi`.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
