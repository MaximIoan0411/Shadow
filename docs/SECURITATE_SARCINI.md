# Securitate — ce trebuie implementat

**Foldere:** `backend/app/security/` (codul care rulează în aplicație) și `security/` (ce nu rulează în aplicație)
**Echipa:** 2 oameni · **Unelte:** Python 3.12, biblioteca `cryptography` sau libsodium, argon2 / bcrypt, PyJWT

Datele de sănătate sunt printre cele mai sensibile, iar o navă e o țintă. Cel mai grav scenariu aici nu e furtul
datelor, ci o **urgență ascunsă** sau o **alarmă falsă** provocată de date modificate. Echipa de securitate face
ca fiecare măsurătoare și fiecare mesaj să poată fi verificat, ca fiecare astronaut să-și vadă doar datele lui și
ca orice acces să lase urmă.

**Regula de bază: fără criptografie proprie.** Doar funcții din biblioteci standard.

**Cum lucrați cu backend-ul:** funcțiile **există deja** în `backend/app/security/`, cu semnăturile finale și
corp provizoriu (secțiunea 12, `contract/security/README.md`). Backend-ul le apelează de la început. Voi înlocuiți
corpul cu varianta reală, fără ca ei să-și schimbe codul.

**Priorități:** `P0` = fără el nu merge demo-ul · `P1` = intră în demo dacă e gata până la ora 16 · `P2` = bonus.

## Cuprins

1. [Modelul de amenințări](#1-modelul-de-amenințări-p0-orele-02)
2. [Parolele](#2-parolele-p0)
3. [Tokenurile](#3-tokenurile-p0)
4. [Blocarea contului](#4-blocarea-contului-p1)
5. [Cine vede ce](#5-cine-vede-ce-p0)
6. [Cheile](#6-cheile-p0)
7. [Semnarea măsurătorilor](#7-semnarea-măsurătorilor-p0)
8. [Sigilarea pachetelor](#8-sigilarea-pachetelor-p0)
9. [Validarea măsurătorilor](#9-validarea-măsurătorilor-p1)
10. [Jurnalul de acces](#10-jurnalul-de-acces-p1)
11. [Atacurile pentru demo](#11-atacurile-pentru-demo-p0)
12. [Funcțiile pe care le apelează backend-ul](#12-funcțiile-pe-care-le-apelează-backend-ul)
13. [Auditul](#13-auditul-p1-ora-1415)
14. [Bonus](#14-bonus-p2)
15. [Împărțirea între cei doi](#15-împărțirea-între-cei-doi)
16. [Cu cine te legi](#16-cu-cine-te-legi)
17. [Scheletele goale](#17-scheletele-goale)

---

## 1. Modelul de amenințări (P0, orele 0–2)

`security/threat-model.md`, `security/architecture.md`.

- **Ce conține:** ce apărăm, de cine și ce atacuri contează, pe o singură pagină.
- **Amenințările de acoperit:**

| Amenințare | Efect | Apărarea |
|---|---|---|
| măsurătoare falsificată | alarmă falsă sau urgență ascunsă | semnătură pe fiecare măsurătoare (§7) |
| senzor defect sau „înghețat” | date greșite care par bune | validare (§9) |
| mesaj modificat între navă și Pământ | ordin medical fals | sigilarea pachetelor (§8) |
| același mesaj retrimis | acțiune repetată | număr de ordine unic (§8) |
| un coleg citește datele altuia | pierderea încrederii, subraportare | conturi separate și reguli de acces (§2–§5) |
| cineva șterge urmele | acces neobservat | jurnal cu hash înlănțuit (§10) |
| token furat de pe stația comună | acces în numele altcuiva | token în memorie, deconectare, revocare (§3) |

- **Mythos:** îl folosește doar Mihai. Echipa îi dă arhitectura și primește înapoi lista de probleme.
- **Gata când:** documentul există și fiecare rând din tabel are un fișier de cod corespondent.

## 2. Parolele (P0)

`backend/app/security/passwords.py`.

- **Ce face:** fiecare astronaut are parola lui. În baza de date stă doar hash-ul.
- **Reguli:**
  - argon2id (sau bcrypt), din bibliotecă; fără MD5 sau SHA simplu;
  - la pornire, seed-ul trece parolele de test prin hash; parola în clar nu ajunge în baza de date sau în jurnale;
  - mesaj unic la autentificare eșuată: „Utilizator sau parolă greșită”, indiferent care dintre ele e greșit;
  - verificarea durează la fel și când utilizatorul nu există.
- **Gata când:** în fișierul SQLite nu se găsește nicio parolă în clar.

## 3. Tokenurile (P0)

`backend/app/security/tokens.py`.

- **Ce face:** după autentificare, contul primește un JWT legat de un singur `crew_id`.
- **Reguli:**
  - HS256, cu secretul din `.env` (`JWT_SECRET`), niciodată scris în cod;
  - conținut: `sub` (id-ul contului), `role`, `crew_id`, `jti` (id unic), `exp` (12 ore);
  - la verificare se acceptă **doar** HS256 (un token cu `alg: none` e respins);
  - `role` și `crew_id` se citesc doar din token; ce trimite clientul în corpul cererii nu dă niciun drept;
  - la deconectare, `jti` intră pe lista de tokenuri revocate până la expirare.
- **Gata când:** după `logout`, același token primește `401`.

## 4. Blocarea contului (P1)

`backend/app/security/lockout.py`.

- **Regula:** 5 parole greșite în 5 minute, pe același cont → `429 too_many_attempts`, cont blocat 60 de secunde
  reale. `details.retry_after_s` spune cât mai e de așteptat.
- Blocarea e pe cont: nu-i afectează pe ceilalți astronauți.
- `POST /sim/reset` șterge blocările (pentru repetiții).
- **Gata când:** testul din `scripts/smoke.py` pentru blocare trece pe backend-ul real.

## 5. Cine vede ce (P0)

`backend/app/deps.py` (împreună cu backend-ul), teste în `backend/tests/security/`.

- **Regulile**, din `contract/README.md`, secțiunea 4:
  - astronautul vede doar datele cu `crew_id`-ul din tokenul lui; nici comandantul nu vede datele unui coleg;
  - ofițerul medical vede alertele de nivel 2 și 3 ale celorlalți, iar fiecare citire a lui se scrie în jurnal;
  - Pământul nu vede nimic în timp real: doar pachetele sosite prin coadă;
  - conținutul unui pachet apare doar după sosire și doar rolului care are voie să-l citească.
- **Ce faceți voi:** un test pentru fiecare rând din tabelul de permisiuni: fiecare rol, pe fiecare tip de
  resursă, cu răspunsul așteptat (`200` sau `403`).
- **Gata când:** testele acoperă tot tabelul și trec.

## 6. Cheile (P0)

`security/keys/generate_keys.py`, `backend/app/security/keys.py`.

- **Ce chei există:**

| Cheie | Tip | La ce folosește |
|---|---|---|
| a navei | Ed25519 | semnează pachetele navă → Pământ |
| a Pământului | Ed25519 | semnează pachetele Pământ → navă |
| a fiecărui dispozitiv | Ed25519 | semnează măsurătorile |
| a legăturii | AES-256, 32 de octeți | criptează pachetele |
| a tokenurilor | secret HS256 | semnează JWT-urile |

- **Reguli:**
  - cheile se generează cu scriptul și **nu intră în git** (`.gitignore` le exclude deja);
  - se încarcă din `.env` sau din fișiere, la pornire; lipsa unei chei oprește pornirea, cu mesaj clar;
  - fiecare cheie are un `key_id`, care apare în pachet.
- **Onest, de spus juriului:** în prototip, cheia legăturii e partajată dinainte. Într-un sistem real ar fi un
  schimb de chei făcut înainte de misiune.
- **Gata când:** `generate_keys.py` produce toate cheile, iar backend-ul pornește cu ele.

## 7. Semnarea măsurătorilor (P0)

`backend/app/security/signing.py`. Folosit de `POST /ingest/measurements` și de simulatorul de dispozitive.

- **Ce face:** fiecare măsurătoare venită de la un dispozitiv are o semnătură Ed25519. O măsurătoare modificată
  după semnare este respinsă.
- **Ce se semnează:** JSON-ul canonic al tuturor câmpurilor în afară de `signature_b64`:
  `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, codificat UTF-8. Semnătura se
  trimite în Base64.
- **Reguli:**
  - cheia publică se caută după `device_id`; un dispozitiv necunoscut e respins;
  - o măsurătoare respinsă nu dă eroare HTTP: răspunsul e `accepted = false`, iar valoarea apare în
    `/security/rejections`, cu motivul `bad_signature`;
  - valorile tastate la check-in nu au semnătură: sunt marcate `source = manual`.
- **Gata când:** schimbarea unei singure cifre într-o măsurătoare semnată duce la respingere.

## 8. Sigilarea pachetelor (P0)

`backend/app/security/sealing.py`. Folosit de coada navă ↔ Pământ.

- **Ce face:** două funcții, `seal` și `open`.
- **`seal(payload, header)`:**
  1. serializează conținutul în JSON canonic;
  2. îl semnează cu cheia expeditorului (Ed25519);
  3. criptează `conținut + semnătură` cu AES-256-GCM, cu un nonce nou de 12 octeți;
  4. antetul pachetului (id, `seq`, direcție, tip, `key_id`) intră ca date asociate (AAD): dacă cineva îl
     modifică, decriptarea eșuează.
- **`open(blob, header)`:** decriptează și verifică semnătura cu cheia publică a expeditorului. La orice eșec
  aruncă `SealError("bad_signature")`.
- **Retrimiterea (replay) o detectează backend-ul**, nu `open`: (`direction`, `seq`) e unic în tabelul de pachete.
  Voi scrieți testul (`replay_packet.py` și `tests/security/test_sealing.py`).
- **Reguli:**
  - nonce-ul nu se refolosește niciodată cu aceeași cheie;
  - în baza de date stă doar forma sigilată.
- **Gata când:** un pachet sigilat cu altă cheie, unul cu antetul modificat și unul retrimis sunt toate respinse.

## 9. Validarea măsurătorilor (P1)

`backend/app/security/validation.py`.

- **Valori imposibile:** fiecare metrică are un interval fizic posibil (de exemplu puls 20–250 bpm, temperatură
  34–41,5 °C). În afara lui → respins, cu motivul `implausible`.
- **Senzor înghețat:** aceeași valoare exactă de prea multe ori la rând → respins, cu motivul `frozen_sensor`.
- **Salt imposibil:** o schimbare prea mare între două citiri apropiate → respins.
- Fiecare respingere apare în `/security/rejections` și pornește evenimentul `measurement.rejected`.
- **Gata când:** `POST /demo/frozen-sensor` produce o respingere vizibilă în interfață.

## 10. Jurnalul de acces (P1)

`backend/app/security/access_log.py`.

- **Ce face:** scrie cine a făcut ce: `login`, `login_failed`, `logout`, citirea datelor unui coleg de către
  ofițerul medical, citirea unei alerte, escaladarea, citirea unui pachet, accesul refuzat.
- **Reguli:**
  - doar se adaugă; nu există funcție de modificare sau de ștergere;
  - fiecare intrare conține hash-ul celei dinainte: `hash = SHA-256(prev_hash + JSON canonic al intrării)`;
  - o funcție `verify_chain()` parcurge jurnalul și spune dacă lanțul e întreg;
  - astronautul vede cine i-a accesat datele; ofițerul medical vede tot jurnalul.
- **Gata când:** modificarea de mână a unei intrări în baza de date e detectată de `verify_chain()`.

## 11. Atacurile pentru demo (P0)

**Scripturile din `security/attacks/` nu se mai fac.** Momentul „atacul” din pitch (3:20–3:50) se arată din
panoul *Demo* al aplicației; restul atacurilor sunt acoperite de teste.

| Atac | Unde se vede |
|---|---|
| pachet semnat cu o cheie greșită | panoul *Demo* → *Spoofed packet* (`POST /demo/inject-spoof`); pachetul apare respins în *Link with the ship* |
| senzor înghețat | panoul *Demo* → *Frozen sensor* (`POST /demo/frozen-sensor`); respingerea apare în *Evidence* |
| măsurătoare modificată după semnare | doar în teste (`backend/tests/security/test_ingest.py`) |
| un astronaut cere datele altuia | doar în teste; în aplicație, încercarea refuzată apare în jurnalul de acces |
| pachet retrimis | nu se arată (vezi `security/checklist.md`) |

## 12. Funcțiile pe care le apelează backend-ul

**Există deja**, cu semnăturile finale și corp provizoriu, în `backend/app/security/`. Referința completă, generată
din cod (cu ce e încă provizoriu): `contract/security/README.md`. Fiecare modul listează funcțiile neterminate în
constanta `PROVIZORIU`; scoateți numele din listă când terminați. `scripts/smoke.py` verifică semnăturile.

| Fișier | Funcții | Cine le apelează |
|---|---|---|
| `errors.py` | `InvalidToken`, `AccountLocked(retry_after_s)`, `SealError(reason)` | backend-ul le transformă în erori API |
| `passwords.py` | `hash(password) -> str`, `verify(password, stored) -> bool`, `DUMMY_HASH` (lente: backend-ul le apelează cu `asyncio.to_thread`) | `db/seed.py`, `services/auth.py` |
| `tokens.py` | `issue(*, user_id, role, crew_id, secret, ttl_s) -> (token, Claims)`, `decode(token, *, secret) -> Claims` (aruncă `InvalidToken`), `async revoke(session, jti, expires_at)`, `async is_revoked(session, jti) -> bool` | `deps.py`, `services/auth.py` |
| `lockout.py` | `check(username)` (aruncă `AccountLocked`), `record_failure(username)`, `clear(username)`, `reset_all()` | `services/auth.py`, `/sim/reset` |
| `keys.py` | `load_keys(*, link_aes_key_b64, keys_dir) -> Keys` | `main.py` (`lifespan`) |
| `signing.py` | `canonical(obj) -> bytes` (**final**), `sign(obj, private_key) -> str`, `verify(obj, signature_b64, public_key) -> bool` | `services/security_log.py`, `simulator/devices.py` |
| `sealing.py` | `seal(payload, header, *, sender) -> bytes`, `open(blob, header) -> dict` (aruncă `SealError("bad_signature")`), `HEADER_FIELDS` | `link/queue.py`, `link/scheduler.py` |
| `validation.py` | `check(metric_key, value, recent_values, limits) -> Issue \| None` | `services/security_log.py`, `services/checkins.py` |
| `access_log.py` | `async write(session, *, at, actor, actor_role, action, resource, crew_id, outcome) -> Entry`, `async verify_chain(session) -> bool`, `entry_hash(prev_hash, fields)` (**final**) | `deps.py`, `services/` |

## 13. Auditul (P1, ora 14–15)

`security/audit/`.

- Mihai rulează Mythos pe codul de securitate și pe regulile de acces; echipa repară ce găsește.
- De verificat de mână, în plus:
  - niciun secret în git (`git log -p` după „secret”, „key”, „password”);
  - CORS deschis doar pentru adresa frontend-ului;
  - niciun endpoint `/crew/…` fără verificarea `crew_access`;
  - mesajele de eroare nu arată detalii interne;
  - tastarea: nicăieri în baza de date nu există caractere, doar timpi.
- **Gata când:** `security/audit/` conține lista problemelor găsite și ce s-a reparat. Se poate arăta juriului.

## 14. Bonus (P2)

- **Criptarea datelor la bord:** câmpurile sensibile din baza de date, criptate cu o cheie din `.env`.
- **Separarea modulelor:** fiecare pilon scrie doar în tabelele lui.
- **Deconectare automată** după un timp fără activitate, pe stația comună.

Planul le menționează, dar se fac doar dacă tot ce e `P0` și `P1` e gata. Ce nu e implementat **nu se prezintă
ca implementat**.

---

## 15. Împărțirea între cei doi

| | Securitate A | Securitate B |
|---|---|---|
| Orele 0–2 | modelul de amenințări, arhitectura; semnăturile funcțiilor, cu backend-ul | generarea cheilor, încărcarea lor |
| Orele 2–10 | parole (§2), tokenuri (§3), cine vede ce (§5) | semnarea măsurătorilor (§7), sigilarea pachetelor (§8) |
| Ora 10 | **prima integrare cap-coadă** | |
| Orele 10–14 | blocarea contului (§4), jurnalul (§10) | validarea (§9), scripturile de atac (§11) |
| Orele 14–15 | **auditul**, împreună cu Mihai | |
| Orele 15–18 | reparații după audit, bonus | reparații după audit, repetiția atacurilor |
| Orele 18–24 | repetiții | repetiții |

Dacă rămâneți în urmă, tăiați în ordinea: bonusul (§14) → saltul imposibil din §9 → blocarea contului (§4).
Nu tăiați: conturile separate, sigilarea pachetelor, pachetul falsificat respins.

## 16. Cu cine te legi

| Cu cine | Ce | Unde | Când se stabilește |
|---|---|---|---|
| **Backend** | funcțiile din secțiunea 12; cine le apelează și unde | `backend/app/security/` ↔ `deps.py`, `routers/`, `link/` | ora 0–1 |
| **Frontend** | tokenul în memorie; pașii la schimbarea astronautului; doar clasa tastei, niciodată litera | `frontend/src/lib/auth.tsx`, colectorul de tastare | ora 0–2 |
| **AI** | serviciul AI nu e expus în afara rețelei interne și primește date doar prin câmpul `context` | `docker-compose.yml` | ora 2–6 |
| **Data** | intervalele fizic posibile ale fiecărei metrici, pentru validare | `data/texts/checkin_indicators.json` | ora 2–6 |

## 17. Scheletele goale

Codul din aplicație:

```
backend/app/security/
├── README.md
├── __init__.py
├── passwords.py
├── tokens.py
├── lockout.py
├── keys.py
├── signing.py
├── sealing.py
├── validation.py
└── access_log.py

backend/tests/security/
├── test_accounts.py         fiecare cont își vede doar datele lui
├── test_permissions.py      tabelul de permisiuni, rând cu rând
├── test_tokens.py           expirare, revocare, alg none
├── test_signing.py          măsurătoare modificată → respinsă
├── test_sealing.py          cheie greșită, antet modificat, replay
└── test_access_log.py       lanțul de hash-uri
```

Ce nu rulează în aplicație:

```
security/
├── README.md
├── threat-model.md
├── architecture.md
├── checklist.md
├── keys/
│   ├── README.md
│   └── generate_keys.py      (cheile generate nu intră în git)
└── audit/
    ├── findings.md           ce s-a găsit, ce s-a reparat, ce a rămas deschis
    └── check_endpoints.py    401 fără token, 403 pentru alt astronaut
```
