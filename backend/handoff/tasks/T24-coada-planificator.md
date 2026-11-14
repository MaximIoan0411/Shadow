# T24 — Coada: planificatorul

**Cine:** A · **Prioritate:** P0 · **Durată estimată:** ~60 min · **Depinde de:** T23 · **Deblochează:** T26, T33

## Ce construiești

Un task din fundal trimite pachetele când fereastra e deschisă, le livrează după întârzierea mediului, le deschide (`sealing.open`) și le marchează livrate sau respinse.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/link/scheduler.py`, `link/windows.py` (schelet)
- `backend/app/security/sealing.py`, `security/errors.py`
- `backend/app/services/events.py`
- `contract/api/README.md` §7.6

## Pași

1. `windows.one_way_delay_s` din `data/environments.json` pentru mediul curent; `window_open` = `True` (prototip).
2. `link_scheduler`: buclă la 1 s, cu sesiune proprie: `queued` → `in_transit` (`sent_at`, `arrives_at = sent_at + delay`) → `packet.sent`; `in_transit` cu `arrives_at <= clock.now()` → `sealing.open` → `delivered` (`payload`, `delivered_at`, `signature_valid=True`) sau `SealError` → `rejected` (`reject_reason`, `signature_valid=False`) → `packet.arrived` / `packet.rejected`.
3. La livrarea unui `earth_reply` cu `alert_id`: `alert.earth_reply = body`, istoric `earth_replied`, `alert.updated` (cu `crew_id`).
4. `GET /crew/{id}/messages`: pachetele `up` livrate pentru membrul acela (și `donki_alert` pentru toți).
5. Evenimentele după commit; bucla nu se oprește la o eroare (log + continuă).
6. Teste (cu `clock.freeze` mutat manual): pachetul ajunge după exact întârzierea mediului; un pachet cu antetul modificat după sigilare e `rejected`; răspunsul Pământului apare la astronaut după a doua întârziere.

## Fișierele atinse

- `app/link/scheduler.py`
- `app/link/windows.py`
- `app/services/link.py`
- `app/main.py`
- `tests/link/test_scheduler.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] în demo, cu ×60 pe Marte (700 s), pachetul ajunge în ~11,7 s reale
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T24 coada: planificatorul`

## Capcane

- Pachetele deja `in_transit` își păstrează `arrives_at` la schimbarea mediului.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
