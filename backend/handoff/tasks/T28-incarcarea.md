# T28 — Pilonul Încărcarea + exerciții

**Cine:** B · **Prioritate:** P1 · **Durată estimată:** ~45 min · **Depinde de:** T16 · **Deblochează:** —

## Ce construiești

Scorul de încărcare osoasă pe sesiune și pe zi, recomandarea de a împărți antrenamentul, seria de zile și proiecția (estimare) a pierderii osoase.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/engine/pillars/musculoskeletal.py` (schelet)
- `backend/app/routers/exercise.py` (mock)
- `data/parameters.json`: `projected_bmd_loss_model`, `alert_strength_drop_level2`, `alert_strength_drop_level3`

## Pași

1. `session_score`: Σ repetări × greutate, cu randament descrescător după primele 5 repetări ale fiecărui set; normalizat ca o zi normală să fie ~80.
2. `daily_loading`: suma; bonus 20% dacă sunt două sesiuni la ≥ 4 ore distanță.
3. `split_recommended`: o singură sesiune făcută/planificată azi.
4. Seria `split_training`: zile consecutive cu antrenament împărțit.
5. `projection`: din ratele lunare din `projected_bmd_loss_model` × aderența; varianta împărțită puțin mai bună; `note` spune că e estimare, demonstrată doar pe animale.
6. Endpoint-urile: `GET …/exercise/today`, `POST …/exercise/sessions` (salvează, `source="manual"`, apoi `dashboard.changed`), `GET …/exercise/sessions`.
7. Teste: a doua sesiune la 7 ore distanță crește scorul zilei cu bonusul; ziua 61 (sărită) dă `split_recommended`.

## Fișierele atinse

- `app/engine/pillars/musculoskeletal.py`
- `app/services/exercise.py`
- `app/routers/exercise.py`
- `tests/engine/test_loading.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T28 pilonul încărcarea + exerciții`

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
