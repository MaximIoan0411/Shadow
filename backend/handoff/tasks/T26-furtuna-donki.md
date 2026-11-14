# T26 — Furtuna: avertizarea DONKI prin coadă

**Cine:** B · **Prioritate:** P1 · **Durată estimată:** ~40 min · **Depinde de:** T24, T25 · **Deblochează:** —

## Ce construiești

Avertizarea Pământului vine ca pachet `donki_alert` pe direcția `up`, cu întârzierea legăturii; la sosire se calculează cu câte minute a fost SHADOW mai rapid (`lead_minutes`).

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/link/queue.py`
- `backend/app/services/radiation.py`
- `data/donki/donki_sep_event.json`
- `contract/api/README.md` §7.7

## Pași

1. La `sep/start`: programează avertizarea Pământului la ora alertei NASA din fișier, relativ la onset (alerta `20240511-AL-006` a venit la 20 min după onset).
2. Când vine momentul (în `live_simulator`): `enqueue(direction="up", kind="donki_alert", payload={"event": SepEvent, "issued_at": …})`.
3. La livrare (în planificator): `earth_warning_arrived_at`; `lead_minutes = (earth_warning_arrived_at − onboard_alert_at)` în minute de misiune.
4. Dacă doza din eveniment trece `prag_doza_eveniment_nivel3` (10% din 250 mGy-Eq) → alertă de nivel 3 → pachet `alert_l3`.
5. Test: cu ceasul mutat, `lead_minutes` e pozitiv și egal cu întârzierea + decalajul alertei NASA.

## Fișierele atinse

- `app/services/radiation.py`
- `app/simulator/live.py`
- `app/link/scheduler.py`
- `tests/link/test_donki_uplink.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T26 furtuna: avertizarea donki prin coadă`

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
