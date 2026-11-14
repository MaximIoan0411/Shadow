# T15 — Motor: triajul

**Cine:** B · **Prioritate:** P0 · **Durată estimată:** ~30 min · **Depinde de:** T14 · **Deblochează:** T16

## Ce construiești

`engine/triage.decide()` transformă constatările în decizii: creează o alertă nouă, o actualizează sau o escaladează; nivelul nu coboară niciodată.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/engine/triage.py` (schelet)
- `backend/app/engine/types.py` (Finding, TriageDecision)

## Pași

1. Pentru fiecare `Finding`: cheia `(crew_id, topic)`.
2. Fără alertă deschisă → `create`.
3. Cu alertă deschisă la nivel ≥ al constatării → `update` (textele și dovezile se actualizează, nivelul rămâne).
4. Cu alertă deschisă la nivel mai mic → `escalate` cu `new_level`.
5. Teste în `tests/engine/test_triage.py`: cele trei cazuri + două constatări pe același subiect în același apel → o singură decizie (cea mai gravă).

## Fișierele atinse

- `app/engine/triage.py`
- `tests/engine/test_triage.py` (nou)

## Gata când

- [ ] `uv run pytest tests/engine -q`
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T15 motor: triajul`

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
