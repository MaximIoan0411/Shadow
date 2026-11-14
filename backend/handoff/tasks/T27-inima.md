# T27 — Pilonul Inima

**Cine:** B · **Prioritate:** P1 · **Durată estimată:** ~45 min · **Depinde de:** T16 · **Deblochează:** —

## Ce construiești

Scorul de pregătire pentru revenire (0–100) din pulsul de repaus, HRV și tensiune, față de baseline-ul din zbor. Praguri derivate, prezentate ca ipoteză.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/engine/pillars/cardio.py` (schelet)
- `data/parameters.json`: `prag_hr_repaus_crestere`, `prag_hrv_lnrmssd`, `prag_tas_scadere_in_zbor`
- `data/catalog/recommendations.json` (cardio-*)

## Pași

1. Puls de repaus: media pe 7 zile > baseline + 1 × CV personal, ≥ 3 zile → `watch`.
2. HRV (lnRMSSD): media pe 7 zile < baseline − 0,5 × CV → `watch`.
3. Ambele, sau unul + simptome la check-in → `Finding(cardio, level 2)`.
4. Scorul: 100 − penalizări; scris în `measurements` ca `landing_readiness` pe zi (pentru grafic și derulator).
5. Înlocuiește valorile mock din panoul Inima (T21).
6. Teste: zilele 110–118 nu există încă (misiunea e în ziua 96) → testează pe serii scrise de mână; pe scenariu, scorul lui cm-2 e ≥ 80 în ziua 96.

## Fișierele atinse

- `app/engine/pillars/cardio.py`
- `app/services/crew.py`
- `tests/engine/test_cardio.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T27 pilonul inima`

## Nu face

- Nu compara cu valorile de pe Pământ: în zbor tensiunea scade normal și pulsul nu crește.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
