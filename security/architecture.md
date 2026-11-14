# SHADOW — arhitectura de securitate

Cum se leagă cheile, semnăturile, criptarea, rolurile și jurnalul. Amenințările sunt în `threat-model.md`.
Codul care rulează e în `backend/app/security/`, cu testele în `backend/tests/security/`.
Căile care încep cu `app/` și `tests/` sunt din `backend/`; celelalte, din rădăcina repo-ului.

```
dispozitiv ──măsurătoare semnată──▶ backend ──cereri cu token──▶ aplicația (fiecare fereastră, sesiunea ei)
                                      │
                                      ├──pachet criptat și semnat──▶ Pământ (întârziere, ferestre de legătură)
                                      │
                                      └──▶ serviciul AI ──▶ model (local, sau pe Colab prin tunel cu cheie)
```

## 1. Chei

Cheile se creează la prima pornire, cu `security/keys/generate_keys.py`, în `security/keys/keys_files/`. Folderul
nu intră în git. Fișierele private pot fi citite doar de proprietar. O cheie existentă nu e înlocuită niciodată.

| Cheie | Tip | Fișier | La ce folosește |
|---|---|---|---|
| a navei | Ed25519 | `private/ship.pem` | semnează pachetele navă → Pământ |
| a Pământului | Ed25519 | `private/earth.pem` | semnează pachetele Pământ → navă |
| a fiecărui dispozitiv | Ed25519 | `public/wearable-cm-N.pem` | verifică măsurătorile acelui dispozitiv |
| a legăturii | AES-256 | `private/earthlink.key` sau `LINK_AES_KEY_B64` | criptează pachetele |
| a tokenurilor | secret HS256 | `JWT_SECRET` din `.env` | semnează tokenurile de acces |

Fără `JWT_SECRET`, sau cu unul mai scurt de 32 de caractere ori publicat în repo, backend-ul folosește un secret
aleator până la repornire. Dacă o cheie lipsește și nu poate fi creată, sau e stricată, pornirea se oprește cu un
mesaj clar (`app/security/keys.py`).

Cheile private ale dispozitivelor stau și ele pe disc, fiindcă dispozitivele sunt simulate de backend. Pe un
dispozitiv real, cheia privată nu părăsește dispozitivul.

## 2. Măsurătorile

`POST /api/v1/ingest/measurements` nu cere token: dovada e semnătura dispozitivului.

Dispozitivul semnează JSON-ul canonic (chei sortate, fără spații) al câmpurilor `device_id`, `crew_id`,
`metric_key`, `value`, `unit`, `measured_at`. Backend-ul verifică, în ordine (`app/services/security_log.py`):

| Pas | Verificare | Respinsă ca |
|---|---|---|
| 1 | semnătura, cu cheia publică a dispozitivului, peste JSON-ul exact cum a sosit | `bad_signature` |
| 2 | dispozitivul e înregistrat pentru acel membru al echipajului (`wearable-cm-2` → `cm-2`) | `bad_signature` |
| 3 | aceeași măsurătoare (dispozitiv, metrică, oră) nu a mai fost primită | `replay` |
| 4 | valoarea e fizic posibilă (limitele din `data/texts/checkin_indicators.json`) | `implausible` |
| 5 | nu e aceeași valoare a 20-a oară la rând de la acel dispozitiv | `frozen_sensor` |

O măsurătoare respinsă nu ajunge la motorul de alerte. Se salvează ca respingere și apare în aplicație, la
*Evidence*. `NaN` și infinit sunt refuzate înainte de pasul 1.

## 3. Pachetele navă ↔ Pământ

Un pachet are un antet vizibil (`id`, `seq`, `direction`, `kind`, `key_id`, `created_at`) și un conținut sigilat
(`app/security/sealing.py`):

```
ciphertext = AES-256-GCM(cheia legăturii, nonce nou de 12 octeți, conținut, date asociate = antetul)
signature  = Ed25519(cheia expeditorului, "shadow-packet-v1" + antet + nonce + ciphertext)
```

- În baza de date și pe drum stă doar forma sigilată (`app/link/queue.py`).
- La sosire, semnătura se verifică **înainte** de decriptare, cu cheia celui care are voie să trimită în acea
  direcție: nava pentru `down`, Pământul pentru `up` (`app/link/scheduler.py`).
- Orice parte schimbată (antet, nonce, conținut) strică semnătura. Pachetul devine `rejected`, cu motivul
  `bad_signature`, și nu se decriptează.
- Cine are doar cheia legăturii poate citi un pachet, dar nu poate fabrica unul: îi lipsește cheia de semnare.
- `seq` e unic pe direcție în tabelul `packets` și face parte din antetul semnat.

## 4. Conturi, parole, tokenuri

- Fiecare astronaut are contul lui. În baza de date stă doar hash-ul parolei, argon2id (`app/security/passwords.py`).
- La autentificare (`app/services/auth.py`): blocare → parolă → token → jurnal. Cinci parole greșite în 5 minute
  blochează acel cont 60 de secunde (`app/security/lockout.py`). Un cont inexistent primește același răspuns, după
  același timp.
- Tokenul e un JWT semnat HS256, valabil 12 ore, cu `sub`, `role`, `crew_id`, `jti` (`app/security/tokens.py`).
- La fiecare cerere (`app/deps.py`): semnătura și expirarea → lista de revocări → contul. Rolul și `crew_id` se
  citesc doar din token.
- Deconectarea trece `jti` pe lista de revocări, în baza de date.
- În aplicație, tokenul stă doar în memoria ferestrei (`frontend/src/lib/api.ts`), nu în `localStorage`. La
  „schimbă astronautul” se opresc colectorul de tastare și fluxul live, iar datele încărcate se șterg
  (`frontend/src/lib/session.tsx`).

## 5. Cine vede ce

| | Astronaut | Ofițer medical | Pământ |
|---|---|---|---|
| datele unui membru (`/crew/{crew_id}/…`) | doar ale lui | ale oricui; citirea se scrie în jurnal | nu |
| alerte | ale lui | ale lui; ale colegilor de la nivelul 2 | doar cele trimise la nivelul 3, ca pachet |
| trimiterea de date pe Pământ | rezumatul săptămânal, doar despre el; nicio alertă | despre oricine; doar el trimite o alertă (escaladarea la nivelul 3) | — |
| conținutul unui pachet | nu; răspunsul Pământului îi ajunge ca mesaj | răspunsurile Pământului și ce a trimis el | pachetele sosite de pe navă |
| jurnalul de acces | intrările despre el | tot | nu |
| valorile respinse | ale lui și cele fără persoană | toate | nu |
| fluxul live (`/events`) | evenimentele lui și cele generale | tot; alertele colegilor de la nivelul 2 | doar misiunea, mediul și pachetele |

Verificarea pentru `/crew/{crew_id}/…` e una singură, `crew_access` din `app/deps.py`. Fără token, toate endpoint-urile
răspund `401`, în afară de `/health`, lista de conturi, autentificarea și primirea măsurătorilor
(`security/audit/check_endpoints.py`).

## 6. Jurnalul de acces

`app/security/access_log.py`, tabelul `access_log`. Se scriu: `login`, `login_failed`, `logout`, `read_dashboard`,
`read_pillar`, `read_alert`, `escalate`, `read_packet`, `access_denied`, `reset`. Citirea propriilor date nu se scrie.

```
hash = SHA-256(prev_hash + JSON canonic al intrării), primele 16 caractere; prima intrare are prev_hash = "0000000000000000"
```

O intrare modificată sau ștearsă din mijloc rupe lanțul. Aplicația îl verifică (`verify_chain`) la pornire și la
`GET /access-log/integrity`; rezultatul apare deasupra jurnalului, iar un lanț rupt e afișat ca alertă și scris în
jurnalul serverului (`app/services/access.py`).

Jurnalul și tokenurile revocate nu se șterg la resetarea simulării; resetarea se scrie și ea în jurnal. Se pierd
însă la repornirea backend-ului, cu setarea implicită. Ce nu poate dovedi lanțul e în `threat-model.md`.

## 7. Medicul AI

- Backend-ul verifică accesul la `crew_id` înainte să trimită întrebarea serviciului AI.
- Serviciul AI răspunde doar backend-ului. Modelul de pe Colab e în spatele unui tunel HTTPS și cere o cheie
  (`llama-server --api-key`). Cheia stă în `ai/.env`, care nu intră în git.
- Răspunsul modelului trece prin `ai/service/guard.py`: întrebare în afara subiectului, medicament, doză sau
  diagnostic → se afișează textul din catalog, marcat ca atare.

## 8. Unde se vede în aplicație

| Ce | Unde |
|---|---|
| pachet falsificat, respins la sosire | panoul *Demo* → *Spoofed packet*, apoi *Link with the ship* |
| senzor înghețat, respins | panoul *Demo* → *Frozen sensor*, apoi *Evidence* |
| un astronaut cere datele altuia | răspuns `403`; încercarea apare în jurnalul de acces |
| jurnalul de acces, cu hash-uri și cu rezultatul verificării lanțului | *Evidence* → *Access log* |
| semnătura și nonce-ul unui pachet | *Link with the ship*, detaliul pachetului |
