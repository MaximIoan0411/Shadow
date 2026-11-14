# SHADOW — auditul de securitate

Ce am verificat, ce am găsit, ce am reparat și ce a rămas deschis. Starea de la 15 noiembrie 2026.

Auditul l-a făcut Mihai, cu Claude (Mythos). Fiecare slăbiciune de mai jos a fost întâi reprodusă pe codul care
rula, apoi reparată, apoi acoperită de un test care pică pe codul vechi.

## 1. Găsite și reparate în aplicație

`backend/app/`. Testele din tabel sunt din `backend/`. Primele treisprezece au fost reparate în PR #9; ultimele trei,
după ce au apărut la scrierea acestui raport.

| Ce se putea face | Reparația | Test |
|---|---|---|
| intrare în orice cont fără parolă: `Authorization: Bearer mock-medic` mergea cu setările implicite | tokenurile de test sunt oprite implicit (`ALLOW_MOCK_TOKENS`) | `tests/security/test_tokens_and_keys.py` |
| token fabricat: secretul implicit era în cod | secret lipsă, scurt sau publicat → secret aleator la pornire | `tests/security/test_tokens_and_keys.py` |
| măsurători false, fără autentificare: orice text trecea drept semnătură | Ed25519, verificat peste JSON-ul exact cum a sosit | `tests/security/test_ingest.py` |
| dispozitivul lui `cm-1` trimitea măsurători pentru `cm-2` | fiecare dispozitiv semnează doar pentru membrul lui | `tests/security/test_ingest.py` |
| aceeași măsurătoare semnată putea fi retrimisă la nesfârșit | a doua copie e respinsă ca `replay` | `tests/security/test_ingest.py` |
| pachetele „sigilate” stăteau în clar în baza de date, fără semnătură | AES-256-GCM și Ed25519; semnătura se verifică înainte de decriptare | `tests/security/test_sealing.py` |
| `NaN` la o măsurătoare dădea eroare 500 | `NaN` și infinit sunt refuzate cu 422 | `tests/security/test_ingest.py` |
| o parolă de 5 MB sau un istoric de chat de 10 MB erau procesate | limite pe toate intrările | `tests/security/test_tokens_and_keys.py` |
| ofițerul medical primea live alertele de nivel 1 ale colegilor | fluxul live respectă regula „de la nivelul 2” | `tests/routers/test_events.py` |
| un astronaut vedea în lista de respingeri măsurătorile colegilor | vede doar ale lui și pe cele fără persoană | `tests/security/test_ingest.py` |
| jurnalul de acces și tokenurile revocate erau în memorie; escaladarea și citirea unui pachet nu se scriau | în baza de date, cu lanț corect și la cereri paralele; nu se șterg la resetare | `tests/security/test_access_log_wiring.py` |
| numele inventate la autentificare rămâneau în memorie | cel mult 10.000 de nume | `tests/security/test_tokens_and_keys.py` |
| erorile 500 nu apăreau nicăieri | se scriu în jurnalul serverului; clientul nu primește detalii | — |
| un astronaut își trimitea propria alertă pe Pământ prin `POST /link/outbox` (`201`), deși escaladarea îi răspundea `403` | o singură regulă: doar ofițerul medical, și doar pentru o alertă ajunsă deja la nivelul 3 | `tests/link/test_enqueue.py` |
| aplicația pornită nu verifica niciodată lanțul jurnalului: o intrare modificată în baza de date nu era semnalată nimănui | lanțul e verificat la pornire și la `GET /access-log/integrity`; rezultatul apare în *Evidence*, deasupra jurnalului | `tests/security/test_access_log_wiring.py` |
| la fiecare pornire, baza de date era ștearsă cu tot cu jurnalul de acces și cu lista tokenurilor revocate: cu un `JWT_SECRET` fix, un token revocat la deconectare răspundea din nou `200` după repornire | la pornire se golesc toate tabelele în afară de aceste două | `tests/routers/test_db_startup.py` |

## 2. Găsite și reparate în prototipurile din `security/`

PR #6. Testele rulează cu `python security/run_tests.py`.

| Unde | Ce se putea face | Reparația |
|---|---|---|
| `tokens/login.py` | un cont inexistent răspundea instant, unul real în ~90 ms: se afla ce conturi există | contul inexistent se verifică față de un hash fals |
| `tokens/login.py` | regula de blocare era alta decât cea din contract | 5 greșeli în 5 minute → 60 s |
| `tokens/login.py` | fiecare nume inventat rămânea în memorie | încercările expirate se uită; cel mult 10.000 de nume |
| `tokens/login.py` | PBKDF2 cu 200.000 de iterații | 600.000 |
| `encryption/packets.py` | semnătura acoperea doar conținutul: un pachet semnat putea fi mutat pe alt astronaut, în altă zi | semnătura acoperă și eticheta |
| `encryption/packets.py` | eticheta `shadow\|crew\|zi` era ambiguă | etichetă JSON |
| `encryption/packets.py` | `aes_key()` crea o cheie nouă pentru orice nume, inclusiv `../escaped` | doar numele cunoscute |
| `audit/audit.py` | ștergerea ultimelor intrări și rescrierea întregului jurnal treceau de `verify()` | `head()` și `verify(path, anchor)` |
| `audit/audit.py` | o linie stricată oprea `verify()` cu excepție | întoarce `(False, poziția)` |
| `measurements/measurements.py` | un mesaj malformat dădea excepție în loc de respingere | `Rejected("malformed message")` |
| `measurements/measurements.py` | nonce-urile și istoricul creșteau la nesfârșit | se țin doar cele care mai contează |

Tot atunci: pe o clonă curată nu rula niciun test (lipsea `keys/generate_keys.py`, trei teste aveau importuri sau
nume greșite), iar un test picat nu oprea scriptul.

## 3. Verificările de mână

| Verificare | Rezultat |
|---|---|
| niciun secret în git | Am căutat în toate commit-urile din `main` chei private, tokenuri, adrese de tunel și fișiere `.env`: nimic. Vezi observația de mai jos. |
| CORS deschis doar pentru interfață | `http://localhost:3000` și `http://127.0.0.1:3000` (`backend/app/config.py`) |
| niciun endpoint `/crew/…` fără `crew_access` | 16 căi, toate răspund `403` altui astronaut |
| niciun endpoint fără token | din 57 verificate, 53 răspund `401`; publice sunt `/health`, lista de conturi, autentificarea și primirea măsurătorilor (semnate). Al 58-lea, fluxul live `/events`, are testul lui (`tests/routers/test_events.py`). |
| mesajele de eroare nu arată detalii interne | eroarea 500 întoarce doar „Unexpected server error.”; validarea întoarce doar câmpul și problema |
| tastarea: în baza de date nu sunt caractere | tabelul `keystroke_sessions` ține doar numărători și medii; o cerere care conține litera primește `422` (`tests/routers/test_keystrokes_api.py`) |

Rândurile 3 și 4 se pot repeta oricând:

```bash
uv run --project backend python security/audit/check_endpoints.py
```

**Observație la primul rând.** Fișierele `backend/shadow.sqlite-wal` și `backend/shadow.sqlite-shm` au intrat de
două ori în git (commit-urile `5731896` și `7a3315b`) și au fost șterse în commit-urile următoare. Conțin hash-urile parolelor
conturilor de test, în formatul vechi. Parolele de test sunt oricum publice, în `backend/seed/users.json`, iar
`.gitignore` exclude acum fișierele bazei de date. De rescris istoricul doar dacă se folosesc vreodată parole reale.

## 4. Deschise

Nereparate.

| Ce | De ce contează |
|---|---|
| nicio limită de cereri pe `/auth/login` și `/ingest/measurements` | cineva din rețea poate bloca un cont câte 60 s, la nesfârșit, sau poate umple lista de respingeri |
| ultimele intrări din jurnal pot fi șterse fără urmă | lanțul arată doar modificările și ștergerile din mijloc; lipsește un hash păstrat în afara jurnalului |
| retrimiterea unui pachet e oprită doar de baza de date | `(direction, seq)` e unic în tabel (cu test), dar nu există o cale de primire din afară pe care s-o încerce un atac, iar motivul de respingere `replay` nu e produs pentru pachete |
| `/sim/*` și `/demo/*` merg cu orice cont | oricine autentificat poate reseta simularea |
| baza de date și cheile private nu sunt criptate pe disc | cine are discul are tot |
| nu există deconectare automată | o sesiune lăsată deschisă pe stația comună rămâne deschisă până la 12 ore |
| blocarea conturilor e în memorie | dispare la repornire |
