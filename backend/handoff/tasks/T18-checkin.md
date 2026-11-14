# T18 — Check-in și decalajul de percepție

**Cine:** A · **Prioritate:** P0 · **Durată estimată:** ~60 min · **Depinde de:** T16 · **Deblochează:** T21

## Ce construiești

Check-in-ul de dimineață se salvează (unul pe zi; câmpurile imposibile respinse, nu eroare), iar decalajul de percepție se calculează din dispoziție și scorurile obiective.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/routers/checkin.py` (mock)
- `backend/app/services/checkins.py`, `engine/perception_gap.py` (schelet)
- `data/texts/checkin_indicators.json` (min/max)
- `engine/derived.py` (PERCEPTION_GAP_*)

## Pași

1. `GET /checkin/schema`: direct din `data.checkin`.
2. `POST`: pentru fiecare câmp numeric în afara `min`/`max` → `FieldRejection(reason="implausible")` și `null`; aceeași valoare exactă 3 zile la rând → `frozen_sensor`.
3. Al doilea check-in în aceeași zi îl **înlocuiește** pe primul (update pe `(crew_id, mission_day)`).
4. `engine/perception_gap.compute`: `self = mood × 20`; `objective` = media scorurilor disponibile (tastare, pvt, puls de noapte, somn); `gap = self − objective`; `watch` ≥ 15, `alert` ≥ 25; explicația în română cu cifrele.
5. Rulează `pipeline.process(…, changed={"temperature_c", "sleep_hours", …})`; întoarce `alerts_created`.
6. Seria de zile (`Streak` `checkin`): zile consecutive cu check-in până azi.
7. Evenimente după commit: `dashboard.changed` (`reason="checkin"`), `alert.created`.
8. Teste: 41,9 °C → în `rejected`, restul salvat; al doilea POST înlocuiește; în ziua 96, dispoziția 4 dă `gap ≥ 25` și `status="alert"` pentru cm-2 (după T19 pentru scorul tastării; până atunci testul folosește scorurile disponibile).

## Fișierele atinse

- `app/services/checkins.py`
- `app/engine/perception_gap.py`
- `app/routers/checkin.py`
- `tests/engine/test_perception_gap.py`, `tests/routers/test_checkin_api.py` (noi)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T18 check-in și decalajul de percepție`

## Capcane

- Răspunsul la o valoare imposibilă e tot **201**, nu 422.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
