# T17 — Alertele: endpoint-urile reale

**Cine:** A · **Prioritate:** P0 · **Durată estimată:** ~60 min · **Depinde de:** T16 · **Deblochează:** T21, T23, T30, T31

## Ce construiești

Toate endpoint-urile de alerte și catalog lucrează cu baza: listă, coada ofițerului medical, detaliu, confirmare, pași, escaladare, închidere.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/routers/alerts.py` (mock)
- `backend/app/services/alerts.py` (schelet)
- `handoff/02_CONTRACT_ENDPOINTS.md` (T17)
- `contract/api/README.md` §4 (cine are voie) și §7.6

## Pași

1. `services/alerts.to_schema(alert)` → `schemas.Alert` (cu `recommendation` din catalog, pașii, istoricul).
2. Liste: `GET /crew/{id}/alerts` (filtre `state`, `topic`; cele mai grave primele; `cmo` vede la alții doar nivel ≥ 2); `GET /cmo/queue` (nivel ≥ 2, nerezolvate).
3. `ack`: doar din `active`, altfel 409 `invalid_state`; istoric `acknowledged`.
4. Pași: `PUT …/plan/steps/{step_id}` bifează/debifează; istoric `step_done`.
5. `escalate`: regulile din router (astronautul nu poate la 3 → 403; nivelul nu coboară → 409). La 3: `# TODO T23` pentru pachet (completezi în T23).
6. `resolve`: astronautul doar nivel 1; `monitoring` mută `recheck_at` cu o zi.
7. Catalogul: din `app.state.data.catalog`, nu din mock.
8. Fiecare acțiune: commit, apoi `alert.updated` (`publish_all`).
9. Teste: firul ack → step → escalate la 2 (astronaut) → escalate la 3 (cmo) → resolve (cmo); erorile 403/409.

## Fișierele atinse

- `app/services/alerts.py`
- `app/routers/alerts.py`
- `tests/routers/test_alerts_api.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T17 alertele: endpoint-urile reale`

## Nu face

- Nu schimba `response_model` sau codurile de eroare ale routerului.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
