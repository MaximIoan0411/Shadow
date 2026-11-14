# SHADOW — lista de verificare

Fiecare cerință din `docs/SECURITATE_SARCINI.md`, cu starea ei, codul și testul care o dovedește. Prima coloană e
secțiunea din acel document. Starea de la 15 noiembrie 2026.

Căile care încep cu `app/` și `tests/` sunt din `backend/`; celelalte, din rădăcina repo-ului.

**Stări:** ✔ făcut și testat · ◐ făcut parțial (scrie ce lipsește) · ✘ nefăcut. Ce nu e ✔ nu se prezintă ca făcut.

## Cum se verifică tot

```bash
(cd backend && uv run pytest tests/security tests/link)               # codul din aplicație
uv run --project backend python scripts/smoke.py                       # contractul și permisiunile
uv run --project backend python security/audit/check_endpoints.py      # 401 fără token, 403 pentru alt astronaut
python security/run_tests.py                                           # prototipurile din security/
```

## Cerințe

| # | Cerință | Stare | Cod | Test |
|---|---|---|---|---|
| 1 | modelul de amenințări și arhitectura, scrise | ✔ | `security/threat-model.md`, `security/architecture.md` | — |
| 2 | parolele: în baza de date stă doar hash-ul (argon2id) | ✔ | `app/security/passwords.py` | `tests/routers/test_seed.py`, `tests/security/test_tokens_and_keys.py` |
| 3 | tokenul e legat de un cont și de un `crew_id`; expiră în 12 ore | ✔ | `app/security/tokens.py` | `tests/security/test_tokens_and_keys.py` |
| 3 | rolul și `crew_id` se citesc doar din token | ✔ | `app/deps.py`, `app/services/auth.py` | `tests/security/test_auth_flow.py` |
| 3 | după deconectare, același token primește `401` | ✔ | `app/security/tokens.py` | `tests/security/test_auth_flow.py` |
| 3 | tokenul stă în memorie, nu în `localStorage` | ✔ | `frontend/src/lib/api.ts` | — |
| 4 | 5 parole greșite în 5 minute blochează contul 60 s, doar pe el | ✔ | `app/security/lockout.py` | `tests/security/test_auth_flow.py`, `scripts/smoke.py` |
| 4 | un cont inexistent primește același răspuns | ✔ | `app/services/auth.py` | `tests/security/test_auth_flow.py` |
| 5 | un astronaut vede doar datele lui | ✔ | `app/deps.py` (`crew_access`) | `security/audit/check_endpoints.py`, `scripts/smoke.py` |
| 5 | ofițerul medical vede alertele colegilor de la nivelul 2; citirile lui se scriu în jurnal | ✔ | `app/services/alerts.py`, `app/deps.py` | `tests/security/test_access_log_wiring.py`, `tests/routers/test_events.py` |
| 5 | Pământul vede doar pachetele sosite, nu și datele echipajului | ✔ | `app/services/link.py`, `app/deps.py` | `tests/link/test_enqueue.py`, `tests/routers/test_events.py`, `scripts/smoke.py` |
| 5 | doar ofițerul medical trimite o alertă pe Pământ | ✔ | `app/services/alerts.py`, `app/services/link.py` | `tests/link/test_enqueue.py` |
| 6 | toate cheile se generează cu un script și nu intră în git | ✔ | `security/keys/generate_keys.py` | `tests/security/test_tokens_and_keys.py` |
| 6 | o cheie lipsă sau stricată oprește pornirea, cu mesaj clar | ✔ | `app/security/keys.py` | `tests/security/test_tokens_and_keys.py` |
| 6 | fiecare pachet poartă un `key_id` | ◐ | `app/link/queue.py` | `tests/link/test_enqueue.py` |
| 7 | o măsurătoare modificată după semnare e respinsă | ✔ | `app/security/signing.py`, `app/services/security_log.py` | `tests/security/test_ingest.py` |
| 7 | un dispozitiv necunoscut, sau care semnează pentru alt membru, e respins | ✔ | `app/services/security_log.py` | `tests/security/test_ingest.py` |
| 8 | un pachet semnat cu altă cheie e respins | ✔ | `app/security/sealing.py` | `tests/security/test_sealing.py`, `tests/routers/test_demo.py` |
| 8 | un pachet cu antetul sau conținutul modificat e respins | ✔ | `app/security/sealing.py`, `app/link/scheduler.py` | `tests/security/test_sealing.py`, `tests/link/test_scheduler.py` |
| 8 | în baza de date stă doar forma sigilată, până la sosire | ✔ | `app/link/queue.py` | `tests/security/test_sealing.py`, `tests/link/test_enqueue.py` |
| 8 | un pachet retrimis e respins | ◐ | `app/db/models/link.py` | `tests/link/test_enqueue.py` |
| 9 | o valoare fizic imposibilă e respinsă | ✔ | `app/security/validation.py` | `tests/security/test_ingest.py` |
| 9 | un senzor înghețat e respins și se vede în interfață | ✔ | `app/security/validation.py`, `app/services/demo.py` | `tests/security/test_ingest.py`, `tests/routers/test_demo.py` |
| 10 | jurnalul de acces: fiecare intrare conține hash-ul celei dinainte | ✔ | `app/security/access_log.py` | `tests/security/test_access_log_wiring.py` |
| 10 | o intrare modificată sau ștearsă e detectată de `verify_chain` și semnalată în aplicație | ✔ | `app/security/access_log.py`, `app/services/access.py` | `tests/security/test_access_log_wiring.py` |
| 10 | astronautul vede cine i-a citit datele; ofițerul medical vede tot | ✔ | `app/services/access.py` | `tests/security/test_access_log_wiring.py` |
| 11 | atacurile pentru demo | ◐ | `app/routers/demo.py`, `app/services/demo.py` | `tests/routers/test_demo.py` |
| 12 | funcțiile din contract au toate corpul real, niciuna provizorie | ✔ | `app/security/`, `contract/security/README.md` | `scripts/smoke.py` |
| 13 | auditul: ce s-a găsit și ce s-a reparat | ✔ | `security/audit/findings.md` | `security/audit/check_endpoints.py` |
| 14 | criptarea datelor în baza de date | ✘ | prototip în `security/encryption/storage.py`, nelegat de aplicație | `security/encryption/test_storage.py` |
| 14 | fiecare pilon scrie doar în tabelele lui | ✘ | — | — |
| 14 | deconectare automată după un timp fără activitate | ✘ | — | — |

## Ce lipsește la cele parțiale

- **6, `key_id`:** apare în antetul fiecărui pachet și e acoperit de semnătură, dar nu există o procedură de
  schimbare a cheilor: e o singură cheie pe expeditor (`ship-2026-01`, `earth-2026-01`).
- **8, pachet retrimis:** `(direction, seq)` e unic în tabelul `packets`, iar `seq` e în antetul semnat; o copie nu
  mai intră în coadă (are test). Motivul de respingere `replay` nu e însă produs pentru pachete, fiindcă legătura e
  simulată în același proces și un pachet nu poate sosi din afară.
- **11, atacurile:** scripturile din `security/attacks/` nu se mai fac. Atacurile se arată din aplicație sau sunt
  acoperite de teste:

| Atac | Unde se vede |
|---|---|
| pachet semnat cu o cheie greșită | panoul *Demo* → *Spoofed packet*; pachetul apare respins în *Link with the ship* |
| senzor înghețat | panoul *Demo* → *Frozen sensor*; respingerea apare în *Evidence* |
| măsurătoare modificată după semnare | doar în teste (`tests/security/test_ingest.py`) |
| un astronaut cere datele altuia | doar în teste; în aplicație, o încercare refuzată apare în jurnalul de acces |
| pachet retrimis | doar în teste (`tests/link/test_enqueue.py`) |
