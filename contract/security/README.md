# SHADOW — contractul backend ↔ securitate

**21 funcții** în `backend/app/security/` · **0 încă provizorii**

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

- Toate funcțiile au corpul **real**: argon2id (`argon2-cffi`), HS256 (`PyJWT`), Ed25519 și AES-256-GCM
  (`cryptography`). Semnăturile lor au rămas cele stabilite de la început, deci codul backend-ului nu s-a schimbat.
- Dacă o funcție redevine provizorie, modulul o trece în constanta `PROVIZORIU`, iar referința de mai jos o
  marchează. Ce e provizoriu **nu se prezintă juriului ca real**.
- La pornire, backend-ul încarcă cheile (`keys.load_keys`) și le dă sigilării (`sealing.configure`).
- Modelul de amenințări și arhitectura sunt în `security/threat-model.md` și `security/architecture.md`; starea
  fiecărei cerințe e în `security/checklist.md`, iar auditul în `security/audit/findings.md`.

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
8. **Măsurătorile de la dispozitive** (`POST /ingest/measurements`): semnătura se verifică peste JSON-ul exact
   cum a sosit, nu peste modelul validat; un dispozitiv poate trimite doar pentru membrul lui de echipaj
   (`keys.DEVICE_CREW`); aceeași măsurătoare (dispozitiv + metrică + oră) primită a doua oară e respinsă ca `replay`.
9. **Jurnalul de acces și tokenurile revocate nu se șterg la `POST /sim/reset`**; resetarea se scrie în jurnal.

## 3. Cine apelează ce

| Funcție | Cine o apelează (backend) |
|---|---|
| `passwords.hash` | `db/seed.py` (conturile de test) |
| `passwords.verify`, `lockout.*` | `routers/auth.py` → `services/auth.py` |
| `tokens.issue`, `tokens.revoke` | `services/auth.py` (login, logout) |
| `tokens.decode`, `tokens.is_revoked` | `deps.py` (`current_user`) |
| `keys.load_keys` | `main.py` (`lifespan`) → `app.state.keys` |
| `signing.canonical`, `signing.sign` | `simulator/devices.py` (folosit de `services/demo.py`, pentru senzorul înghețat din demo) |
| `signing.verify` | `services/security_log.py` (`POST /ingest/measurements`) |
| `sealing.seal` | `link/queue.py` (la crearea pachetului) |
| `sealing.open` | `link/scheduler.py` (la sosire) |
| `validation.check` | `services/security_log.py`, `services/checkins.py` |
| `access_log.write` | `deps.py` (acces refuzat, citirea datelor unui coleg de către ofițerul medical), `services/auth.py` |
| `access_log.verify_chain` | doar testele de securitate; aplicația pornită nu o apelează încă |

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
backend-ul și testele.

---

## 5. Referința funcțiilor

Generată din `backend/app/security/`.

### `security/errors.py`

Excepțiile pe care le aruncă pachetul de securitate. Backend-ul le prinde și le transformă în erori API.

| Nume și semnătură | Tip | Provizoriu | Ce face |
|---|---|---|---|
| clasa `InvalidToken` | — | — | Token lipsă, malformat, expirat, cu alt algoritm decât HS256 sau revocat. Backend: 401 `unauthorized`. |
| clasa `AccountLocked` | — | — | Prea multe parole greșite pe acest cont. Backend: 429 `too_many_attempts`, cu `retry_after_s` în details. |
| clasa `SealError` | — | — | Un pachet nu poate fi deschis. Backend: pachetul devine `rejected`, cu `reject_reason = reason`. Retrimiterea (`replay`) NU o detectează sealing, ci backend-ul (unic pe direcție + seq). |

### `security/passwords.py`

Parolele: în baza de date stă doar hash-ul. Fiecare astronaut are parola lui.

ATENȚIE, backend: ambele funcții sunt LENTE intenționat. Din cod asincron se apelează cu
`await asyncio.to_thread(passwords.verify, parola, hash_salvat)`.

| Nume și semnătură | Tip | Provizoriu | Ce face |
|---|---|---|---|
| `hash(password: str) -> str` | sync | nu | Întoarce hash-ul parolei, cu sare aleatoare inclusă, gata de salvat în `users.password_hash`. |
| `verify(password: str, stored: str) -> bool` | sync | nu | True dacă parola corespunde hash-ului. Durează la fel indiferent unde diferă (comparare în timp constant). |

Constante: `MAX_PASSWORD_CHARS = 256`

### `security/tokens.py`

Tokenurile de acces (JWT, HS256). Fiecare token e legat de un singur cont și un singur `crew_id`.

| Nume și semnătură | Tip | Provizoriu | Ce face |
|---|---|---|---|
| clasa `Claims` | — | — | Claims(sub: str, role: str, crew_id: str \| None, jti: str, exp: int) Câmpuri: `sub`, `role`, `crew_id`, `jti`, `exp` |
| `issue(*, user_id: str, role: str, crew_id: str \| None, secret: str, ttl_s: int = 43200) -> tuple[str, app.security.tokens.Claims]` | sync | nu | Emite un token nou. Întoarce tokenul (text) și conținutul lui (pentru jurnal și pentru `expires_in`). |
| `decode(token: str, *, secret: str) -> app.security.tokens.Claims` | sync | nu | Verifică semnătura, algoritmul (doar HS256) și expirarea. Aruncă InvalidToken. NU verifică revocarea: aceea cere baza de date, vezi `is_revoked`. |
| `revoke(session: Any, jti: str, expires_at: datetime.datetime) -> None` | **async** | nu | Trece tokenul pe lista de revocări până la expirare (la `logout`). Se apelează în tranzacția cererii. |
| `is_revoked(session: Any, jti: str) -> bool` | **async** | nu | True dacă tokenul a fost revocat. Backend-ul o apelează după `decode`, la fiecare cerere. |

Constante: `TTL_S = 43200`, `ALGORITHM = 'HS256'`, `REQUIRED_CLAIMS = ('exp', 'sub', 'role', 'jti')`

### `security/lockout.py`

Blocarea contului după prea multe parole greșite. Blocarea e PE CONT: nu-i afectează pe ceilalți astronauți.

Regula: 5 parole greșite în 5 minute reale → cont blocat 60 de secunde reale. Starea stă în memorie (se pierde la
repornire, ceea ce e acceptabil pentru prototip). Timpul e cel REAL, nu cel al misiunii.

| Nume și semnătură | Tip | Provizoriu | Ce face |
|---|---|---|---|
| `check(username: str) -> None` | sync | nu | Aruncă AccountLocked dacă acest cont e blocat. Se apelează ÎNAINTE de verificarea parolei. |
| `record_failure(username: str) -> None` | sync | nu | O parolă greșită. La a 5-a în fereastra de 5 minute, contul se blochează. |
| `clear(username: str) -> None` | sync | nu | Autentificare reușită: șterge încercările greșite ale contului. |
| `reset_all() -> None` | sync | nu | Pentru `POST /sim/reset`: șterge toate blocările. |

Constante: `MAX_ATTEMPTS = 5`, `WINDOW_S = 300`, `LOCK_S = 60`, `MAX_TRACKED = 10000`

### `security/keys.py`

Cheile. Se generează cu security/keys/generate_keys.py și NU intră în git.

| Cheie                 | Tip              | La ce folosește                     |
| a navei               | Ed25519          | semnează pachetele navă → Pământ    |
| a Pământului          | Ed25519          | semnează pachetele Pământ → navă    |
| a fiecărui dispozitiv | Ed25519          | semnează măsurătorile               |
| a legăturii           | AES-256 (32 B)   | criptează pachetele                 |
| a tokenurilor         | secret HS256     | semnează JWT-urile (din JWT_SECRET) |

Fișierele stau în `<keys_dir>/keys_files/` (`private/` și `public/`), sau în folderul din variabila de mediu
`SHADOW_KEYS_DIR` (folosită de teste, ca să nu atingă cheile reale). La pornire, cheile care lipsesc sunt create
cu `<keys_dir>/generate_keys.py`; o cheie existentă nu e niciodată înlocuită. Dacă o cheie nu poate fi nici citită,
nici creată, pornirea se oprește cu un mesaj clar.

| Nume și semnătură | Tip | Provizoriu | Ce face |
|---|---|---|---|
| clasa `KeysError` | — | — | O cheie lipsește sau e stricată. Pornirea se oprește. |
| clasa `Keys` | — | — | Keys(ship_key_id: str, earth_key_id: str, ship_private: bytes, earth_private: bytes, link_aes_key: bytes, device_public: dict[str, bytes] = <factory>, device_private: dict[str, bytes] = <factory>, device_crew: dict[str, str] = <factory>) Câmpuri: `ship_key_id`, `earth_key_id`, `ship_private`, `earth_private`, `link_aes_key`, `device_public`, `device_private`, `device_crew` |
| `load_keys(*, link_aes_key_b64: str = '', keys_dir: str = '../security/keys') -> app.security.keys.Keys` | sync | nu | Încarcă toate cheile la pornire (din lifespan). Rezultatul se ține în `app.state.keys`. |

Constante: `KEYS_DIR_ENV = 'SHADOW_KEYS_DIR'`, `GENERATOR = 'generate_keys.py'`, `SHIP_KEY_ID = 'ship-2026-01'`, `EARTH_KEY_ID = 'earth-2026-01'`, `LINK_KEY_FILE = 'earthlink.key'`, `AES_KEY_BYTES = 32`

### `security/signing.py`

Semnăturile Ed25519 ale măsurătorilor venite de la dispozitive (POST /ingest/measurements).

CE SE SEMNEAZĂ (fixat în contract, folosit identic de simulator, de backend și de scripturile de atac):
JSON-ul canonic al tuturor câmpurilor măsurătorii, în afară de `signature_b64`, produs de `canonical()`.

Backend-ul verifică semnătura peste obiectul JSON EXACT cum a sosit, nu peste modelul validat: după validare `61`
devine `61.0`, iar ora își schimbă scrierea, deci forma canonică n-ar mai fi cea semnată de dispozitiv.

| Nume și semnătură | Tip | Provizoriu | Ce face |
|---|---|---|---|
| `canonical(obj: dict[str, typing.Any]) -> bytes` | sync | nu | JSON canonic: chei sortate, fără spații, UTF-8, fără câmpul `signature_b64`. NU e provizoriu. |
| `sign(obj: dict[str, typing.Any], private_key: bytes) -> str` | sync | nu | Semnează măsurătoarea; întoarce semnătura în Base64. Folosită de simulatorul de dispozitive. |
| `verify(obj: dict[str, typing.Any], signature_b64: str, public_key: bytes \| None) -> bool` | sync | nu | True dacă semnătura e validă pentru `obj` cu cheia publică a dispozitivului. Dispozitiv necunoscut (`public_key is None`) → False. Nu aruncă excepții: orice problemă înseamnă False. |

### `security/sealing.py`

Sigilarea pachetelor dintre navă și Pământ: semnătură Ed25519 + criptare AES-256-GCM.

`header` = plicul pachetului, vizibil: {"id", "seq", "direction", "kind", "key_id", "created_at"}. Intră ca date
asociate (AAD): dacă cineva îl modifică, deschiderea eșuează. `payload` = conținutul (secțiunea 7.6 din
contract/api/README.md descrie ce conține, după `kind`).

Cum e făcut un pachet sigilat (JSON, cu câmpurile în Base64):
    ciphertext = AES-256-GCM(cheia legăturii, nonce nou de 12 octeți, payload canonic, AAD = antetul canonic)
    signature  = Ed25519(cheia expeditorului, "shadow-packet-v1" + antet canonic + nonce + ciphertext)
Semnătura se verifică ÎNAINTE de decriptare, cu cheia publică a celui care are voie să trimită în acea direcție
(`down` = nava, `up` = Pământul). Cine are doar cheia legăturii nu poate fabrica un pachet: îi lipsește cheia
de semnare. Cine schimbă antetul, nonce-ul sau conținutul strică semnătura.

Retrimiterea aceluiași pachet (replay) NU se verifică aici, ci de backend: (direction, seq) e unic în tabel.

| Nume și semnătură | Tip | Provizoriu | Ce face |
|---|---|---|---|
| `configure(keys: app.security.keys.Keys) -> None` | sync | nu | Apelată o dată, la pornire (din lifespan), cu cheile încărcate de `keys.load_keys`. |
| `seal(payload: dict[str, typing.Any], header: dict[str, typing.Any], *, sender: str = 'ship') -> bytes` | sync | nu | Semnează (cheia lui `sender`: "ship" sau "earth") și criptează. Întoarce octeții de salvat în `packets.sealed`. |
| `open(blob: bytes, header: dict[str, typing.Any]) -> dict[str, typing.Any]` | sync | nu | Decriptează și verifică semnătura expeditorului. Întoarce `payload`. Aruncă SealError("bad_signature") la orice problemă: cheie greșită, antet modificat, conținut modificat. |

Constante: `HEADER_FIELDS = ('id', 'seq', 'direction', 'kind', 'key_id', 'created_at')`, `DOMAIN = b'shadow-packet-v1'`, `NONCE_BYTES = 12`, `SENDER_OF_DIRECTION = {'down': 'ship', 'up': 'earth'}`, `ATTACKER = 'attacker'`

### `security/validation.py`

Validarea măsurătorilor: valori imposibile și senzori „înghețați”.

Limitele fizic posibile vin din data/texts/checkin_indicators.json (`min`, `max`) și din `EXTRA_LIMITS` de mai
jos, pentru metricile care nu apar la check-in. Backend-ul încarcă ultimele valori și le dă funcției.

| Nume și semnătură | Tip | Provizoriu | Ce face |
|---|---|---|---|
| clasa `Issue` | — | — | Issue(kind: Literal['implausible', 'frozen_sensor'], message: str) Câmpuri: `kind`, `message` |
| `check(metric_key: str, value: float, recent_values: list[float], limits: dict[str, tuple[float, float]]) -> app.security.validation.Issue \| None` | sync | nu | None = valoarea e acceptată. `recent_values` = ultimele valori ale aceluiași dispozitiv, cea mai nouă ultima. `limits` = limitele din checkin_indicators.json, completate de backend cu EXTRA_LIMITS. |

Constante: `FROZEN_REPEATS = 20`

### `security/access_log.py`

Jurnalul de acces: doar se adaugă; fiecare intrare conține hash-ul celei dinainte.

hash = SHA-256( prev_hash + JSON canonic al intrării fără câmpurile `hash` și `prev_hash` ), în hex, primele 16 caractere
afișate. Prima intrare are prev_hash = "0" * 16.

Acțiuni: login, login_failed, logout, read_dashboard, read_pillar, read_alert, escalate, read_packet,
access_denied, reset.

Jurnalul stă în tabelul `access_log` și NU se șterge la `POST /sim/reset`. Lanțul arată o intrare modificată sau
ștearsă din mijloc; ștergerea ultimelor intrări se vede doar dacă ultimul hash e păstrat și în altă parte.

| Nume și semnătură | Tip | Provizoriu | Ce face |
|---|---|---|---|
| clasa `Entry` | — | — | Entry(id: int, at: datetime.datetime, actor: str, actor_role: str, action: str, resource: str, crew_id: str \| None, outcome: Literal['allowed', 'denied'], prev_hash: str, hash: str) Câmpuri: `id`, `at`, `actor`, `actor_role`, `action`, `resource`, `crew_id`, `outcome`, `prev_hash`, `hash` |
| `entry_hash(prev_hash: str, fields: dict[str, typing.Any]) -> str` | sync | nu | NU e provizoriu: formula lanțului, folosită și de `verify_chain`. |
| `write(session: Any, *, at: datetime.datetime, actor: str, actor_role: str, action: str, resource: str, crew_id: str \| None, outcome: Literal['allowed', 'denied']) -> app.security.access_log.Entry` | **async** | nu | Adaugă o intrare. Se apelează în tranzacția cererii; nu face commit. |
| `verify_chain(session: Any) -> bool` | **async** | nu | True dacă niciun rând nu a fost modificat sau șters (lanțul de hash-uri e întreg). |

Constante: `GENESIS = '0000000000000000'`, `FIELDS = ('id', 'at', 'actor', 'actor_role', 'action', 'resource', 'crew_id', 'outcome')`

