# T29 — Semnale încrucișate + cauza de mediu

**Cine:** B · **Prioritate:** P1 · **Durată estimată:** ~45 min · **Depinde de:** T16 · **Deblochează:** —

## Ce construiești

Trei abateri mici din piloni diferiți la același om devin un semnal încrucișat; aceeași abatere la cel puțin 3 din 4 membri în aceeași zi înseamnă cauză de mediu (cabina), nu individuală.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/engine/cross_signals.py` (schelet)
- `engine/derived.py` (ENVIRONMENTAL_MIN_CREW, CROSS_SIGNAL_WINDOW_DAYS)
- `data/scenario/scenario.json` (zilele 40–41: somn prost la toți)

## Pași

1. `environmental_cause`: grupează constatările zilei pe subiect; ≥ 3 membri → subiectul are cauză de mediu.
2. În `pipeline`: rulează pentru toți membrii în aceeași zi (în replay e natural; live, după fiecare zi nouă); setează `cause="environmental"` și `cause_explanation` („Aceeași abatere la 4 din 4 membri: problema e probabil în cabină.”).
3. `detect`: semnalele din ultimele 3 zile la același om, din ≥ 2 piloni → `CrossSignal` cu `confidence` și explicație; apare în `dashboard.cross_signals`.
4. Teste: în ziua 40 alertele de somn/tastare au `cause="environmental"`; alerta imunitară a lui cm-2 are `individual`; cm-2 în ziua 96 are un semnal încrucișat (imunitar + comportamental).

## Fișierele atinse

- `app/engine/cross_signals.py`
- `app/services/pipeline.py`
- `app/services/crew.py`
- `tests/engine/test_cross_signals.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T29 semnale încrucișate + cauza de mediu`

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
