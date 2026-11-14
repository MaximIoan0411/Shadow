# SHADOW — contractul backend ↔ securitate

**{{N_FUNCTIONS}} funcții** în `backend/app/security/` · **{{N_PROVISIONAL}} încă provizorii**

Codul de securitate rulează în același proces cu backend-ul. Contractul dintre cele două echipe sunt **numele,
parametrii, tipurile întoarse și excepțiile** funcțiilor de mai jos. Backend-ul le apelează; echipa de securitate
le scrie.

## Cuprins

1. [Cum lucrăm](#1-cum-lucrăm)
2. [Regulile pentru backend](#2-regulile-pentru-backend)
3. [Cine apelează ce](#3-cine-apelează-ce)
4. [Ce e fixat și ce nu](#4-ce-e-fixat-și-ce-nu)
5. [Referința funcțiilor](#5-referința-funcțiilor)

---

## 1. Cum lucrăm

- Toate funcțiile **există deja**, cu semnăturile finale. Multe au corp **provizoriu**: suficient ca backend-ul să
  lucreze, fără criptografie reală. Fiecare modul le listează în constanta `PROVIZORIU`, iar referința de mai jos
  le marchează. Când termină o funcție, echipa de securitate îi scoate numele din listă.
- Backend-ul le apelează de la început. Echipa de securitate înlocuiește corpul cu varianta reală (argon2id, PyJWT,
  Ed25519 și AES-GCM din `cryptography`), **fără să schimbe semnăturile**, deci fără să atingă codul backend-ului.
- **Până la ora 12** nu mai rămâne niciun `# PROVIZORIU`. Ce rămâne provizoriu **nu se prezintă juriului ca real**.
- Modelul de amenințări și arhitectura sunt în `security/threat-model.md` și `security/architecture.md`.

## 2. Regulile pentru backend

1. **Funcțiile lente se apelează în afara buclei asincrone.** `passwords.hash` și `passwords.verify` sunt lente
   intenționat:
   ```python
   ok = await asyncio.to_thread(passwords.verify, parola, hash_salvat)
   ```
2. **Funcțiile asincrone primesc sesiunea cererii** (`tokens.revoke`, `tokens.is_revoked`, `access_log.write`,
   `access_log.verify_chain`) și scriu în aceeași tranzacție. Nu fac `commit`.
3. **Excepțiile se transformă în erori API**, în backend:

   | Excepție | Eroare API |
   |---|---|
   | `InvalidToken` | `401 unauthorized` |
   | `AccountLocked(retry_after_s)` | `429 too_many_attempts`, cu `details.retry_after_s` |
   | `SealError(reason)` | pachetul devine `rejected`, cu `reject_reason = reason` (nu e eroare HTTP) |

4. **Retrimiterea unui pachet (replay) o detectează backend-ul**, nu `sealing`: (`direction`, `seq`) e unic în
   tabelul `packets`, iar un `seq` deja văzut înseamnă `rejected` cu `reject_reason = "replay"`.
5. **Utilizator inexistent la login:** backend-ul verifică totuși parola contra `passwords.DUMMY_HASH`, ca
   răspunsul să dureze la fel (nu se poate afla dacă un cont există).
6. **Ordinea la login:** `lockout.check` → `passwords.verify` → `lockout.record_failure` sau `lockout.clear` →
   `tokens.issue` → `access_log.write`.
7. **Ordinea la fiecare cerere autentificată:** `tokens.decode` → `tokens.is_revoked` → încărcarea contului.
   `role` și `crew_id` se citesc **doar din token**.

## 3. Cine apelează ce

| Funcție | Cine o apelează (backend) |
|---|---|
| `passwords.hash` | `db/seed.py` (conturile de test) |
| `passwords.verify`, `lockout.*` | `routers/auth.py` → `services/auth.py` |
| `tokens.issue`, `tokens.revoke` | `services/auth.py` (login, logout) |
| `tokens.decode`, `tokens.is_revoked` | `deps.py` (`current_user`) |
| `keys.load_keys` | `main.py` (`lifespan`) → `app.state.keys` |
| `signing.canonical`, `signing.sign` | `simulator/devices.py`, `security/attacks/*` |
| `signing.verify` | `services/security_log.py` (`POST /ingest/measurements`) |
| `sealing.seal` | `link/queue.py` (la crearea pachetului) |
| `sealing.open` | `link/scheduler.py` (la sosire) |
| `validation.check` | `services/security_log.py`, `services/checkins.py` |
| `access_log.write` | `deps.py` (acces refuzat, citirea datelor unui coleg de către ofițerul medical), `services/auth.py` |
| `access_log.verify_chain` | `GET /evidence/*`, testele de securitate |

## 4. Ce e fixat și ce nu

| Fixat (nu se schimbă fără acordul ambelor echipe) | Liber (echipa de securitate decide) |
|---|---|
| numele modulelor și ale funcțiilor | biblioteca folosită (argon2-cffi, PyJWT, cryptography) |
| parametrii, tipurile întoarse, excepțiile | formatul intern al hash-ului și al pachetului sigilat |
| ce se semnează: `signing.canonical()` | parametrii de cost ai hash-ului |
| câmpurile antetului unui pachet: `sealing.HEADER_FIELDS` | unde se țin cheile pe disc |
| formula jurnalului: `access_log.entry_hash()` | |
| regula de blocare: 5 greșeli în 5 minute → 60 s | |

`signing.canonical()` și `access_log.entry_hash()` **nu sunt provizorii**: le folosesc identic simulatorul,
backend-ul și scripturile de atac.

---

## 5. Referința funcțiilor

Generată din `backend/app/security/`.

{{REFERENCE}}
