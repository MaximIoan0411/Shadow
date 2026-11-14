# T23 — Coada: crearea pachetelor

**Cine:** A · **Prioritate:** P0 · **Durată estimată:** ~60 min · **Depinde de:** T17 · **Deblochează:** T24

## Ce construiești

Pachetele se creează sigilate în tabelul `packets`: din escaladarea la nivelul 3, din rezumatul aprobat (`/link/outbox`) și din răspunsul Pământului (`/earth/replies`).

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/link/queue.py` (schelet)
- `backend/app/security/sealing.py`
- `backend/app/routers/link.py` (mock)
- `backend/app/db/models/link.py`
- `contract/api/README.md` §7.6 (ce conține `payload` după `kind`)

## Pași

1. `link/queue.enqueue`: `id = next_id("pk")`, `seq = next_seq(direction)`, `header = {id, seq, direction, kind, key_id, created_at}` (`sealing.HEADER_FIELDS`), `sealed = sealing.seal(payload, header, sender="ship" | "earth")`, `size_bytes = len(sealed)`, `status="queued"`.
2. Escaladarea la nivelul 3 (T17, `# TODO T23`): `enqueue(kind="alert_l3", payload={"alert": <Alert ca JSON>, "note": …})`, `alert.packet_id`, istoric `packet_sent`. Același lucru în `pipeline` pentru nivel 3 automat.
3. `POST /link/outbox` (weekly_summary / alert_l3), `POST /earth/replies` (`direction="up"`, `kind="earth_reply"`, `payload={"body", "alert_id"}`).
4. `GET /link/packets` (filtre, cele mai noi primele; `progress` și `eta_real_s` calculate la răspuns), `GET /link/packets/{id}` (`payload` doar dacă `delivered` și rolul are voie, altfel `null`; `crypto` din antet).
5. Teste: escaladarea la 3 creează un pachet `queued` cu `seq` 1; al doilea are `seq` 2; `earth` nu vede `payload` până la livrare.

## Fișierele atinse

- `app/link/queue.py`
- `app/services/link.py`
- `app/services/alerts.py`
- `app/services/pipeline.py`
- `app/routers/link.py`
- `tests/link/test_enqueue.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T23 coada: crearea pachetelor`

## Nu face

- Nu salva conținutul în clar la creare: doar `sealed`. `payload` se completează la livrare (T24).

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
