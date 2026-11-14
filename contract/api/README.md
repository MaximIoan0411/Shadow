# SHADOW — contractul API (frontend ↔ backend)

**NASA Space Apps 2026 · versiunea 1.2.0 · 58 endpoint-uri · 98 modele**

Acest document este **înțelegerea dintre frontend și backend**. Dacă amândouă părțile îl respectă, se pot construi
separat și se potrivesc la integrare. Tot ce e aici rulează: `backend/` este **serverul real** (bază de date,
motor de triaj, coadă spre Pământ, securitate), iar textele, mediile, catalogul și pragurile vin din `data/`.

Contractele cu restul aplicației sunt în același folder: `contract/ai/` (backend ↔ serviciul AI),
`contract/security/` (backend ↔ codul de securitate) și `contract/data/` (backend ↔ fișierele din `data/`).

> Prototip de sprijin pentru decizie, nu dispozitiv medical.

> **Nou în 1.2 — aliniat cu planul de backend și cu structura repo-ului.**
> - Misiunea **pornește în ziua 96**: zilele 1–95 sunt istoric. `GET /crew/{id}/timeline` întoarce doar zilele care
>   au avut loc (implicit și maximum: ziua curentă).
> - `?as_of_day=` mai mare decât ziua curentă → `422 validation_error`.
> - `PUT /sim/clock` cu `mission_day` merge doar **înainte**; înapoi → `409 invalid_state` (folosiți `/sim/reset`).
> - `POST /sim/reset` repornește ceasul la ziua 96 și trimite `dashboard.changed` cu `reason = "reset"`.
> - `AiStatus.mode` poate fi și `"mock"` (serviciul AI încă fără model).
> - Fără schimbări de câmpuri sau de căi: frontend-ul scris pe 1.1 merge în continuare.
> - Căile s-au mutat: contractul e în `contract/api/`, uneltele în `scripts/`, clientul în `frontend/src/lib/`.
>
> **Nou în 1.1 — autentificare separată pentru fiecare astronaut.** Nu mai există contul comun `astronaut`: fiecare
> membru al echipajului are contul și parola lui. Au apărut `GET /auth/accounts` și `POST /auth/logout`, eroarea
> `429 too_many_attempts` și câmpul `initials` pe `User`. Utilizatorii de test s-au schimbat (secțiunea 1), iar
> tokenurile de test (doar cu `ALLOW_MOCK_TOKENS=true`) sunt `mock-specialist2`, `mock-medic` etc. Detalii: secțiunea 4.

## Ce citești, în funcție de ce faci

| Dacă lucrezi la… | Citește | Apoi |
|---|---|---|
| **Frontend** | secțiunile 1–7 și 10 | pornește backend-ul, generează tipurile TypeScript, construiește pe datele scenariului |
| **Backend** | secțiunile 1–9, apoi `backend/PLAN_DE_ATAC_BACKEND.md` | înlocuiește pe rând corpul funcțiilor din `backend/app/routers/` cu servicii reale |
| **Securitate** | secțiunile 3, 4, 8 și `contract/security/README.md` | înlocuiește corpul funcțiilor provizorii din `backend/app/security/` |
| **Medicul AI** | `contract/ai/README.md`; aici doar `/ai/*` | serviciul din `ai/`, pe portul 8001 |

## Cuprins

1. [Pornire în 2 minute](#1-pornire-în-2-minute)
2. [Ce e în dosar](#2-ce-e-în-dosar)
3. [Reguli generale](#3-reguli-generale)
4. [Autentificare și roluri](#4-autentificare-și-roluri)
5. [Erori](#5-erori)
6. [Evenimente live (SSE)](#6-evenimente-live-sse)
7. [Fluxuri cap-coadă](#7-fluxuri-cap-coadă)
8. [Cine implementează ce](#8-cine-implementează-ce)
9. [Cum schimbăm contractul](#9-cum-schimbăm-contractul)
10. [Frontend: tipuri și client](#10-frontend-tipuri-și-client)
11. [Referința endpoint-urilor](#11-referința-endpoint-urilor)
12. [Modelele de date](#12-modelele-de-date)

---

## 1. Pornire în 2 minute

```bash
cd backend
uv sync                                              # instalează exact ce e în uv.lock
uv run uvicorn app.main:app --reload --port 8000
```

Fără `uv`, varianta clasică: `python -m venv .venv && source .venv/bin/activate && pip install -e .`, apoi
`uvicorn app.main:app --reload --port 8000`. Serverul citește `data/` din rădăcina repo-ului (sau din `DATA_DIR`).

- **http://localhost:8000/docs** — documentație interactivă (Swagger). Apeși „Authorize”, lipești un token și poți
  încerca orice endpoint din browser.
- **http://localhost:8000/health** — verifică dacă serverul răspunde.

**Conturi de test — câte unul pentru fiecare astronaut.** Fiecare are altă parolă (valorile de test sunt în
`backend/seed/users.json`):

| Utilizator | Parolă de test | Rol | Membru de echipaj | Ecranul lui |
|---|---|---|---|---|
| `comandant` | `cm1-shadow` | `astronaut` | `cm-1` Comandant | corpul interactiv, check-in |
| `specialist2` | `cm2-shadow` | `astronaut` | `cm-2` Specialist de misiune 2 (**are alertele din scenariu**) | corpul interactiv, check-in |
| `medic` | `cm3-shadow` | `cmo` | `cm-3` Ofițer medical de bord | coada ofițerului medical + propriile date |
| `inginer` | `cm4-shadow` | `astronaut` | `cm-4` Inginer de zbor | corpul interactiv, check-in |
| `earth` | `earth-shadow` | `earth` | — | Controlul misiunii |

Primul apel, din terminal:

```bash
curl -s localhost:8000/api/v1/auth/accounts          # conturile pentru ecranul „Cine ești?”

curl -s -X POST localhost:8000/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"username":"specialist2","password":"cm2-shadow"}'
# → {"access_token":"eyJhbGciOi…", "user": {"role":"astronaut","crew_id":"cm-2", ...}}

TOKEN=eyJhbGciOi…   # access_token din răspunsul de mai sus
curl -s localhost:8000/api/v1/crew/cm-2/dashboard -H "Authorization: Bearer $TOKEN"   # 200, datele lui
curl -s localhost:8000/api/v1/crew/cm-1/dashboard -H "Authorization: Bearer $TOKEN"   # 403, nu sunt ale lui
```

Scenariul: **ziua 96 din 140, ora 07:00, tranzit spre Marte**. Misiunea pornește din acest punct; zilele 1–95
sunt istoric, iar zilele 97–140 nu au avut loc încă. Specialist de misiune 2 are o alertă imunitară de nivel 2
(puls de noapte +7 bpm, 3 nopți) și una comportamentală de nivel 1 (tastare mai lentă cu 18%). Ceilalți trei membri
ai echipajului au totul „în limite”: autentificați-vă cu conturi diferite ca să vedeți că fiecare își primește
propriile date.

Verificare că totul e întreg (rulați înainte de fiecare commit pe contract):

```bash
# din rădăcina repo-ului
uv run --project backend python scripts/smoke.py        # toate endpoint-urile, permisiunile, datele, contractul AI
uv run --project backend python scripts/build_docs.py   # regenerează tot folderul contract/
```

## 2. Ce e în dosar

Contractul stă în `contract/`, iar codul care îl implementează, în folderele echipelor.

```
contract/
├── README.md                ← cuprinsul contractelor (scris de mână)
├── api/                     ← ACEST document: frontend ↔ backend
│   ├── guide.md             ← partea scrisă de mână (aici se editează)
│   ├── README.md            ← generat: ghidul + referința + modelele
│   └── openapi.yaml/.json   ← generate
├── ai/                      ← backend ↔ serviciul AI (aceeași organizare)
├── security/                ← backend ↔ backend/app/security/ (semnăturile funcțiilor)
└── data/                    ← backend ↔ data/ (JSON Schema pentru fiecare fișier)

backend/app/
├── schemas.py               ← SURSA DE ADEVĂR pentru acest contract: toate modelele API
├── main.py                  ← create_app(), lifespan, forma erorilor, OpenAPI
├── deps.py                  ← autentificare, roluri, difuzorul SSE
├── routers/                 ← câte un fișier pe domeniu; aici intră logica reală (prin services/)
├── services/, engine/, link/, simulator/, db/   ← logica reală (vezi secțiunea 8)
├── datafiles.py             ← formatul fișierelor din data/ + încărcarea lor
├── ai_schemas.py            ← copie a ai/service/schemas.py
└── security/                ← al echipei de securitate (Ed25519, AES-256-GCM, HS256, argon2id)

frontend/src/lib/
├── shadow-api.d.ts          ← tipuri TypeScript generate din contract/api/openapi.json
└── api.ts                   ← client: fetch cu token, login/logout, SSE, colectorul de tastare

scripts/
├── build_docs.py            ← generează tot contract/
├── smoke.py                 ← verifică tot: endpoint-uri, permisiuni, date, contractul AI
├── request_examples.py      ← o cerere de exemplu pentru fiecare endpoint (API și AI)
└── gen_types.sh             ← regenerează tipurile TypeScript
```

## 3. Reguli generale

**Adresa de bază:** `http://localhost:8000/api/v1`. Toate căile din document sunt complete (încep cu `/api/v1`).

**Format:** JSON, UTF-8, la cereri și la răspunsuri. Numele câmpurilor sunt în engleză, `snake_case`. Textele pentru
utilizator (titluri, explicații, mesaje de eroare) vin de la backend **în română, gata de afișat**; frontend-ul nu
le traduce și nu le compune.

**Câmpuri lipsă:** un câmp opțional fără valoare vine ca `null`, nu lipsește din răspuns.

### Timpul

Aplicația are **două ceasuri**. Confuzia dintre ele e cea mai probabilă sursă de bug-uri.

| | Timpul misiunii | Timpul real |
|---|---|---|
| Ce este | ora de pe navă, dată de `SimClock` | ceasul de pe perete, din sala de demo |
| Cât de repede merge | de `time_scale` ori mai repede (implicit ×60) | normal |
| Unde apare | **toate** câmpurile dată-oră: `created_at`, `arrives_at`, `sim_now`… | doar câmpurile care se termină în `_real_s` |
| La ce folosește | ce afișați utilizatorului | durata animațiilor (bara de progres a pachetului) |

- Datele-oră sunt ISO 8601 în UTC, de exemplu `2027-04-15T07:42:00Z`.
- `mission_day` numără zilele de la **1**. Misiunea are 140 de zile și **pornește în ziua 96, la 07:00**
  (zilele 1–95 sunt istoric generat la pornirea serverului). Zilele de după ziua curentă nu există încă.
- Întârzierea legăturii: `one_way_delay_s` e în secunde de misiune (700 s ≈ 11 min 40 s), iar
  `one_way_delay_real_s` e aceeași durată în secunde reale (700 / 60 ≈ 11,7 s). **Animațiile folosesc varianta `_real_s`.**
- Backend: nicăieri `datetime.now()`. Mereu `clock.now()`.

### Identificatori

Texte scurte cu prefix, generate de backend. Frontend-ul le tratează ca texte opace.

| Prefix | Ce este | Exemplu |
|---|---|---|
| `cm-` | membru de echipaj | `cm-2` |
| `al-` | alertă | `al-1042` |
| `pk-` | pachet din coada navă ↔ Pământ | `pk-0007` |
| `ck-` | check-in | `ck-0096` |
| `st-` | pas din planul unei alerte (unic în alerta lui) | `st-2` |
| `ex-`, `pvt-`, `rj-`, `rm-`, `xs-`, `ev-` | sesiune de exerciții, test de reacție, respingere, reamintire, semnal încrucișat, eveniment SSE | |
| `<topic>-<nivel>-<nr>` | recomandare din catalog | `immune-2-1` |

### Starea (semaforul)

Un singur câmp, `status`, peste tot. Culoarea nu apare niciodată singură: e însoțită de formă și de cuvânt.

| `status` | Culoare | Formă | Cuvânt | Înseamnă |
|---|---|---|---|---|
| `ok` | mint `#7cf3d6` | ● | „În limite” | ca normalul personal |
| `watch` | warn `#f5c66b` | ▲ | „De urmărit” | abatere mică sau scurtă |
| `alert` | danger `#ff6b6b` | ■ | „Alertă” | abatere peste prag |
| `unknown` | gri (`fg-4`) | ○ | „Fără date” | baseline-ul nu e gata sau lipsesc date |

### Nivelurile de triaj

`level` e un număr, nu un text.

| `level` | Cine se ocupă | Cine vede alerta |
|---|---|---|
| `1` | astronautul, singur, cu pașii din catalog | doar astronautul |
| `2` | ofițerul medical de la bord | astronautul + ofițerul medical |
| `3` | medicul de pe Pământ | astronautul + ofițerul medical + Pământul (prin coadă, cu întârziere) |

### De unde vine o valoare

Câmpul `source` de pe fiecare valoare: `device` (de la un dispozitiv, semnată), `manual` (tastată la check-in),
`simulated` (generată de simulator). **Afișați eticheta „date simulate” oriunde `source = simulated` sau
`data_is_simulated = true`.** E o cerință de onestitate față de juriu.

### Unități

| Mărime | Unitate | Observație |
|---|---|---|
| tensiune | mmHg | |
| puls | bpm | |
| glicemie | mg/dL | |
| temperatură | °C | |
| somn | ore, cu zecimale | `5.5` = 5 h 30 min |
| timpi de tastare și de reacție | ms | |
| rata dozei | µSv/h | |
| doza acumulată | mSv | prototipul afișează totul în Sv, simplificat |
| scoruri | 0–100 | 100 = exact ca baseline-ul personal |

### Chei de metrici

Câmpul `key` / `metric_key`. Lista e fixă; adăugați aici înainte să folosiți una nouă.

| Cheie | Pilon | Ce este |
|---|---|---|
| `keys_per_min`, `hold_ms_mean`, `flight_ms_mean`, `backspace_rate` | behavioral | trăsăturile tastării |
| `pvt_mean_speed`, `pvt_lapses` | behavioral | testul de reacție |
| `systolic_mmhg`, `diastolic_mmhg`, `resting_pulse_bpm`, `hrv_lnrmssd`, `landing_readiness` | cardio | |
| `night_pulse_bpm`, `temperature_c`, `sleep_hours`, `stress_index` | immune | |
| `loading_score`, `strength_pct` | musculoskeletal | |
| `glucose_mg_dl` | — | general, din check-in |
| `dose_rate_usv_h` | — | radiații |

### Piloni, nume și zone

| `pillar` | Numele din interfață | `body_zone` | Pericolul principal |
|---|---|---|---|
| `behavioral` | Tastatura | `brain` | izolarea |
| `cardio` | Inima | `heart` | gravitația |
| `immune` | Santinela | `immune` | mediul închis și ostil |
| `musculoskeletal` | Încărcarea | `bones` | gravitația |

## 4. Autentificare și roluri

### Fiecare astronaut are contul lui

**Nu există cont comun de echipaj.** Fiecare membru are un cont, o parolă și un `crew_id` propriu. De ce contează:

- **Baseline-ul e personal.** SHADOW compară fiecare om cu el însuși. Dacă doi astronauți ar folosi același cont,
  tastarea și valorile lor s-ar amesteca și comparația n-ar mai însemna nimic.
- **Datele sunt ale astronautului.** Un coleg nu le poate deschide (`403`), nici măcar comandantul. Doar ofițerul
  medical vede alertele de nivel 2 și 3 ale altcuiva, iar fiecare citire a lui rămâne în jurnal.
- **Jurnalul de acces are nume.** „Cine a citit ce” are sens doar dacă fiecare acțiune e legată de o persoană.
- **Cauză individuală sau de mediu.** Motorul de triaj compară membrii echipajului între ei (aceeași abatere la mai
  mulți = probabil cabina), deci are nevoie de date separate pe fiecare om.

| Cont | Câte | `role` | `crew_id` |
|---|---|---|---|
| astronaut | câte unul pe membru (3 în seed) | `astronaut` | al lui, unic |
| ofițer medical de bord | 1 (este și el membru al echipajului) | `cmo` | al lui, unic |
| medicul de zbor de pe Pământ | 1 | `earth` | `null` |

Ofițerul medical are **ambele** calități: își vede propriile date ca orice astronaut (`/crew/cm-3/…`) și are, în
plus, coada ofițerului medical.

### Pașii

1. `GET /api/v1/auth/accounts` (fără token) → conturile pentru ecranul „Cine ești?”: câte o casetă cu nume și inițiale.
2. Utilizatorul își alege caseta și își scrie parola → `POST /api/v1/auth/login` → `access_token` + `user`.
3. La **fiecare** cerere următoare: antetul `Authorization: Bearer <access_token>`.
4. Fără token, cu token expirat sau revocat → `401 unauthorized`. Frontend-ul duce utilizatorul la ecranul „Cine ești?”.
5. La plecarea de la stația de lucru: `POST /api/v1/auth/logout`.

### Schimbarea astronautului pe aceeași stație de lucru

La bord, mai mulți oameni folosesc același ecran. Ordinea e obligatorie, ca datele unuia să nu rămână pe ecran
pentru următorul:

1. `POST /auth/logout`;
2. oprește colectorul de tastare și închide conexiunea `/events`;
3. șterge din memorie tokenul și **toate** datele încărcate (stare React, cache de cereri);
4. arată ecranul „Cine ești?”;
5. după `login` cu noul cont: deschide din nou `/events` și încarcă datele lui.

Afișați mereu, vizibil, cine e autentificat (nume + inițiale, în antet). Tastarea se atribuie contului autentificat.

### Reguli pentru conturi (backend și securitate)

- **Parole:** în baza de date stă doar hash-ul (argon2 sau bcrypt), niciodată parola. Conturile de test se creează
  din `backend/seed/users.json`, care nu conține parole reale.
- **Tokenul:** JWT semnat HS256, cu `sub` (id-ul contului), `role`, `crew_id`, `jti` (id unic al tokenului) și
  `exp` (12 ore). `role` și `crew_id` se citesc **doar din token**; un `crew_id` trimis de client în corpul cererii
  nu dă niciun drept.
- **Deconectare:** `jti` intră pe lista de tokenuri revocate până la expirare.
- **Parole greșite:** 5 în 5 minute pe același cont → `429 too_many_attempts`, cont blocat 60 de secunde reale.
  Blocarea e pe cont, deci nu-i afectează pe ceilalți astronauți.
- **Mesaj unic:** „Utilizator sau parolă greșită”, indiferent care dintre ele e greșit.
- **Jurnal:** `login`, `login_failed` și `logout` se scriu în jurnalul de acces, cu contul și ora.
- **Fără conturi noi din aplicație:** echipajul e fix, stabilit înainte de misiune. Nu există endpoint de înregistrare.

**Doar pentru teste**, cu `ALLOW_MOCK_TOKENS=true` în `.env`, backend-ul acceptă și tokenul `mock-<utilizator>`
(de exemplu `mock-specialist2`), FĂRĂ parolă; acesta nu se revocă la `logout`. Implicit e oprit: într-un demo sau
pe o rețea cu alți oameni ar însemna că oricine intră în orice cont.

### Ce are voie fiecare rol

| Resursă | `astronaut` | `cmo` | `earth` |
|---|---|---|---|
| Datele proprii (`/crew/{id}/…` cu `crew_id`-ul contului) | da | da | — |
| Datele altui membru (`/crew/{alt_id}/…`) | **nu (403)**, nici comandantul | da, se scrie în jurnal | nu (403) |
| Alertele proprii | toate | toate | — |
| Alertele altui membru | nu | doar nivelul 2 și 3 | doar ce ajunge prin pachete |
| Escaladare la nivelul 2 | da | da | nu |
| Escaladare la nivelul 3 | **nu** | da | nu |
| Retrimiterea unei alerte de nivel 3 (`/link/outbox`, `alert_l3`) | **nu (403)** | da | nu |
| Rezumatul săptămânal (`/link/outbox`, `weekly_summary`) | doar despre el | da | nu |
| Coada de pachete | nu | da | da |
| Răspuns de pe Pământ (`/earth/replies`) | nu | nu | da |
| Dozimetrul în timp real (`/radiation/status`) | da | da | **nu** |
| Jurnalul de acces | doar accesul la datele lui | tot | nu |
| Verificarea jurnalului (`/access-log/integrity`) | da | da | nu |
| Butoanele de demo (`/sim/*`, `/demo/*`) | da | da | da |

Coloana `astronaut` e valabilă pentru **fiecare** cont de astronaut în parte: „datele proprii” înseamnă cele cu
`crew_id`-ul din tokenul lui.

Principiul: **datele sunt ale astronautului**. Pământul nu vede nimic în timp real, ci doar pachetele care au ajuns
prin coadă, după întârziere. De aceea rolul `earth` nu are acces la niciun endpoint `/crew/…`.

Rolurile permise sunt scrise la fiecare endpoint în [referință](#11-referința-endpoint-urilor), la „Cine poate apela”.

## 5. Erori

Orice eroare, de la orice endpoint, are **aceeași formă**:

```json
{
  "error": {
    "code": "forbidden",
    "message": "Nu ai acces la datele altui membru al echipajului.",
    "details": null
  }
}
```

- `code` — text stabil, pentru logica din frontend. Nu se schimbă.
- `message` — în română, se poate afișa direct utilizatorului.
- `details` — opțional. La `validation_error` conține lista câmpurilor greșite.

| HTTP | `code` | Când apare | Ce face frontend-ul |
|---|---|---|---|
| 401 | `unauthorized` | lipsește tokenul sau a expirat | trimite la login |
| 401 | `invalid_credentials` | utilizator sau parolă greșită | mesaj sub formular |
| 429 | `too_many_attempts` | 5 parole greșite în 5 minute pe același cont | mesaj + numărătoare inversă din `details.retry_after_s` |
| 403 | `forbidden` | rolul nu are voie sau datele sunt ale altcuiva | afișează `message` |
| 404 | `not_found` | id inexistent | afișează `message` |
| 409 | `invalid_state` | acțiunea nu se potrivește cu starea (ex. confirmi o alertă deja rezolvată) | reîncarcă resursa |
| 422 | `validation_error` | datele nu respectă contractul | marchează câmpurile din `details.fields` |
| 500 | `internal_error` | eroare neașteptată | mesaj generic + buton „încearcă din nou” |

Exemplu de `422`:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Datele trimise nu respectă contractul.",
    "details": { "fields": [ { "field": "mood", "problem": "Input should be less than or equal to 5" } ] }
  }
}
```

**Două cazuri care NU sunt erori** (răspunsul e 2xx):

- **Valoare imposibilă la check-in** (ex. temperatură 41,9 °C). Check-in-ul se salvează, iar câmpul apare în lista
  `rejected` din răspuns, cu un mesaj de afișat lângă el. Un singur câmp greșit nu trebuie să blocheze tot formularul.
- **Medicul AI nu răspunde.** `/ai/chat` întoarce textul din catalog, cu `fallback = true`. Aplicația merge și fără AI.

## 6. Evenimente live (SSE)

`GET /api/v1/events` ține o conexiune deschisă prin care backend-ul împinge schimbările. **Nu faceți polling.**
Regula: la un eveniment, reîncărcați resursa pe care o privește, sau actualizați direct starea din `data`.

Fiecare mesaj arată așa:

```
id: ev-000123
event: alert.created
data: {"id":"ev-000123","type":"alert.created","at":"2027-04-15T07:42:00Z","crew_id":"cm-2","data":{…}}
```

| `type` | Când vine | Forma lui `data` | Ce face frontend-ul |
|---|---|---|---|
| `mission.tick` | la ~1 secundă reală | [MissionTick](#missiontick) | actualizează ceasul și ziua misiunii |
| `environment.changed` | s-a schimbat mediul | [MissionState](#missionstate) | actualizează comutatorul și întârzierea afișată |
| `dashboard.changed` | după check-in, exerciții, test de reacție, reverificare, salt de zi, reset | `{ "reason": "checkin" \| "exercise" \| "pvt" \| "keystrokes" \| "recheck" \| "jump" \| "reset" }` | reîncarcă `dashboard` și panoul deschis; la `reset`, reîncarcă **tot** (ca după o reconectare) |
| `alert.created` | triajul a creat o alertă | [AlertBrief](#alertbrief) | notificare + reîncarcă `dashboard` |
| `alert.updated` | confirmare, pas bifat, escaladare, închidere, răspuns sosit | [AlertBrief](#alertbrief) | reîncarcă alerta dacă e deschisă |
| `packet.sent` | pachetul a plecat (s-a deschis fereastra) | [Packet](#packet) | pornește bara de progres, durată `eta_real_s` |
| `packet.arrived` | pachetul a ajuns și semnătura e validă | [Packet](#packet) | mută rândul la „SOSIT”; la bord: reîncarcă `messages` |
| `packet.rejected` | semnătură invalidă, replay sau decriptare eșuată | [Packet](#packet) | rând roșu „RESPINS” |
| `radiation.alert` | dozimetrul a trecut pragul | [RadiationStatus](#radiationstatus) | banner „Mergi în adăpost” pe tot ecranul |
| `radiation.reading` | citire nouă în timpul furtunii (max. una la 2 s reale) | [RadiationStatus](#radiationstatus) | adaugă punctul pe grafic |
| `radiation.cleared` | rata a revenit la normal | [RadiationStatus](#radiationstatus) | ascunde banner-ul |
| `measurement.rejected` | o valoare de la un dispozitiv a fost respinsă | [Rejection](#rejection) | rând nou în ecranul de securitate |
| `reminder.due` | a venit ora unei reamintiri | [Reminder](#reminder) | reamintire discretă |

Cine primește ce:

- `astronaut` — evenimentele cu `crew_id` egal cu al lui și pe cele generale (`crew_id = null`).
- `cmo` — toate.
- `earth` — doar `mission.tick`, `environment.changed` și `packet.*`.

Detalii de conexiune:

- La 15 secunde fără evenimente, serverul trimite un comentariu `: ping`.
- La deconectare, clientul se reconectează singur. **Evenimentele pierdute nu se retrimit**: după reconectare,
  reîncărcați datele ecranului curent.
- `EventSource` din browser nu poate trimite antetul `Authorization`. Folosiți `@microsoft/fetch-event-source`
  (exemplul e în `frontend/src/lib/api.ts`).

## 7. Fluxuri cap-coadă

Fiecare flux e lista de apeluri, în ordine. „→ SSE” înseamnă ce evenimente pornesc de la acel apel.

### 7.1 Pornirea aplicației și autentificarea

1. `GET /auth/accounts` → casetele de pe ecranul „Cine ești?” (la bord: conturile cu `location = "ship"`).
2. Utilizatorul își alege contul și își scrie parola → `POST /auth/login` → token și `user` (cu `role` și `crew_id`).
3. `GET /mission` → ora, ziua, mediul, întârzierea.
4. Deschide `GET /events` și ține-l deschis cât e autentificat acest cont.
5. După rol: `astronaut` → 7.2, cu `crew_id`-ul lui; `cmo` → `GET /cmo/queue`; `earth` → `GET /link/packets`.
6. La schimbarea astronautului: `POST /auth/logout`, apoi pașii din secțiunea 4.

De acum, `{id}` din toate fluxurile înseamnă `user.crew_id` al contului autentificat.

### 7.2 Ecranul astronautului

1. `GET /crew/{id}/dashboard` → culorile celor 4 zone, decalajul de percepție, banner-ul alertei, seriile, reamintirile.
2. Click pe o zonă → `GET /crew/{id}/pillars/{pillar}` → panoul complet (funcție, pericol, valori, grafic, plan, surse).
3. Bifează un pas → `PUT /alerts/{alert_id}/plan/steps/{step_id}` → SSE `alert.updated`.
4. „Întreabă medicul AI” → `POST /ai/chat` cu `alert_id`.

### 7.3 Check-in-ul de dimineață

1. `GET /crew/{id}/checkins/today` → dacă e `null`, afișează formularul.
2. `GET /checkin/schema` → câmpurile, textele explicative și limitele.
3. `POST /crew/{id}/checkins` → răspunsul conține `rejected` (câmpuri de remăsurat), `perception_gap` (de afișat
   imediat) și `alerts_created`. → SSE `dashboard.changed`, eventual `alert.created`.
4. Dacă utilizatorul a scris o notă, ritmul tastării s-a trimis în paralel, ca la 7.4, cu `context = "checkin_note"`.

### 7.4 Tastarea (fără conținut)

1. La primul `keydown` într-un câmp urmărit: generează un `session_id` (UUID).
2. La fiecare `keydown`/`keyup`: salvează `performance.now()` și **clasa** tastei (`char`, `space`, `backspace`,
   `enter`, `other`). **Niciodată `event.key`.**
3. La 5 secunde sau la 200 de taste: `POST /crew/{id}/keystrokes/batches`.
4. Răspunsul are trăsăturile sesiunii și abaterea față de baseline → actualizează barele live.
5. Cardul „Ritmul tău” și comparația din demo: `GET /crew/{id}/keystrokes/summary`.

### 7.5 Testul de reacție

Testul de 3 minute rulează în frontend. La sfârșit: `POST /crew/{id}/pvt` cu toate încercările → rezultatul.
→ SSE `dashboard.changed`.

### 7.6 De la alertă la răspunsul Pământului (pasul 3)

Acesta e firul principal al demo-ului.

| # | Cine | Apel | Ce se întâmplă |
|---|---|---|---|
| 1 | backend | — | triajul creează alerta de nivel 1 → SSE `alert.created` |
| 2 | astronaut | `POST /alerts/{id}/ack` | `state = acknowledged` |
| 3 | astronaut | `POST /alerts/{id}/escalate` `{ "to_level": 2 }` | apare în `/cmo/queue` → SSE `alert.updated` |
| 4 | cmo | `GET /alerts/{id}` | citirea se scrie în jurnalul de acces |
| 5 | cmo | `POST /alerts/{id}/escalate` `{ "to_level": 3 }` | backend-ul semnează, criptează și pune pachetul în coadă; `packet_id` apare pe alertă |
| 6 | backend | — | fereastra e deschisă → pachetul pleacă → SSE `packet.sent` |
| 7 | earth | `GET /link/packets` | vede pachetul `in_transit`, cu `progress` și `eta_real_s` |
| 8 | backend | — | după `one_way_delay_s`: decriptare, verificarea semnăturii → SSE `packet.arrived` |
| 9 | earth | `GET /link/packets/{id}` | `payload` conține acum alerta decriptată |
| 10 | earth | `POST /earth/replies` | răspunsul intră în coadă pe direcția `up` → SSE `packet.sent` |
| 11 | backend | — | după încă o întârziere → SSE `packet.arrived` (cu `crew_id`) și `alert.updated` |
| 12 | astronaut | `GET /crew/{id}/messages` sau `GET /alerts/{id}` | vede răspunsul (`earth_reply`) |

Ce conține `payload`, după `kind`:

| `kind` | `payload` |
|---|---|
| `alert_l3` | `{ "alert": Alert, "note": text }` |
| `weekly_summary` | `{ "crew_id": text, "week": număr, "summary": text }` |
| `earth_reply` | `{ "body": text, "alert_id": text \| null }` |
| `donki_alert` | `{ "event": SepEvent, "issued_at": dată-oră }` |

Ciclul de viață al unui pachet: `queued` → `in_transit` → `delivered` **sau** `rejected`.
`progress = (acum − sent_at) / (arrives_at − sent_at)`, limitat la 0–1.

Pachetul falsificat pentru demo: `POST /demo/inject-spoof` → SSE `packet.rejected`.

### 7.7 Furtuna solară (pasul 4)

| # | Cine | Apel | Ce se întâmplă |
|---|---|---|---|
| 1 | oricine | `POST /sim/sep/start` | simulatorul redă evenimentul DONKI din 11 mai 2024 |
| 2 | backend | — | rata dozei urcă → SSE `radiation.reading` |
| 3 | backend | — | 3 citiri peste 2× media pe 24 h → alertă de nivel 1 → SSE `radiation.alert` și `alert.created` |
| 4 | astronaut | `POST /radiation/shelter-ack` `{ "sheltered": true }` | se aplică ecranarea; se salvează ora |
| 5 | backend | — | avertizarea Pământului circulă ca pachet `donki_alert`, direcția `up` → SSE `packet.sent` |
| 6 | backend | — | pachetul ajunge → SSE `packet.arrived`; `lead_minutes` se completează |
| 7 | frontend | `GET /radiation/status` | afișează „Adăpost activ cu N minute înainte de avertizarea Pământului” |
| 8 | backend | — | rata revine la normal → SSE `radiation.cleared` |

Dacă doza din eveniment trece pragul de nivel 3, backend-ul trimite singur un pachet `alert_l3` spre Pământ.

### 7.8 Derulatorul misiunii

1. La pornire: `GET /crew/{id}/timeline` → starea fiecărui pilon pe fiecare zi **care a avut loc** (la început,
   zilele 1–96). Bara are `total_days` poziții (din `/mission`); zilele de după ziua curentă se desenează „încă nu”.
2. La `mission.tick`, dacă s-a schimbat `mission_day`, reîncarcă `timeline`.
3. Când utilizatorul se oprește pe o zi: `GET /crew/{id}/dashboard?as_of_day=N` și, dacă e un panou deschis,
   `GET /crew/{id}/pillars/{pillar}?as_of_day=N`. `N` nu poate depăși ziua curentă (altfel 422).
4. Derulatorul doar **citește** istoricul. Nu schimbă ceasul misiunii. Pentru demo, `PUT /sim/clock` cu
   `mission_day` sare **înainte** (backend-ul generează zilele lipsă); înapoi nu se poate, doar prin `/sim/reset`.

### 7.9 Comutatorul de mediu

`GET /environments` pentru listă, `PUT /mission/environment` pentru schimbare → SSE `environment.changed`.
Se schimbă întârzierea legăturii, rata de doză de fond și pragurile care depind de gravitație.

### 7.10 Securitate și dovezi

- `GET /access-log` — cine a citit ce.
- `GET /access-log/integrity` — verifică lanțul de hash-uri al întregului jurnal; `intact = false` înseamnă că o
  intrare a fost modificată sau ștearsă direct în baza de date. Se afișează deasupra jurnalului.
- `GET /security/rejections` — valori și pachete respinse.
- `POST /demo/frozen-sensor` — demo cu senzor înghețat → SSE `measurement.rejected`.
- `GET /evidence/tests` — rezultatele testelor automate.
- `GET /evidence/parameters` — pragurile din `parameters.json`, fiecare cu sursa lui.

## 8. Cine implementează ce

Contractul fixează **ce** se vede din afară. **Cum** se construiește backend-ul (straturi, bază de date asincronă,
pornire din ziua 96, task-uri din fundal, ordinea pe ore) e în `backend/PLAN_DE_ATAC_BACKEND.md`, iar lista
funcționalităților, în `BACKEND_SARCINI.md`. Pe scurt:

| Modul | Unde | Ce face |
|---|---|---|
| Fundație | `main.py` (`create_app`, `lifespan`), `config.py`, `clock.py`, `db/` | baza SQLite asincronă, recreată la fiecare pornire; `SimClock`; încărcarea `data/` cu `datafiles.load_all()` |
| Autentificare | `routers/auth.py`, `deps.py` | conturile din `backend/seed/users.json`, tokenuri reale, revocare, jurnal (funcțiile vin din `security/`) |
| Simulator | `simulator/` | zilele 1–96 la pornire, din `data/scenario/scenario.json`; datele live; furtuna |
| Motor | `engine/` (funcții pure) | baseline, cei patru piloni, decalajul de percepție, cauza de mediu, triajul, cu pragurile din `data/parameters.json` |
| Servicii | `services/` | fiecare router apelează un serviciu; `services/pipeline.py` = drumul oricărei date noi |
| Coada | `link/` | planificatorul, ferestrele, întârzierea; sigilarea vine din `security/sealing.py` |
| Medicul AI | `routers/ai.py` | apelul către serviciul AI (`contract/ai/`), limită de 20 s, fallback pe catalog |
| Securitate | `security/` (echipa de securitate) | funcțiile din `contract/security/README.md` |

**Regula de aur pentru backend:** schimbați doar **corpul** funcțiilor. Calea, parametrii, `response_model` și
forma erorilor rămân. Dacă trebuie altfel, vedeți secțiunea următoare.

Detalii pe care contractul le fixează pentru echipa de securitate (implementate în `backend/app/security/`):

- **Semnătura unei măsurători** (`/ingest/measurements`): Ed25519 peste `signing.canonical(obj)`, adică JSON-ul
  canonic al tuturor câmpurilor în afară de `signature_b64` (chei sortate, fără spații, UTF-8). Semnătura, în Base64.
- **Un pachet:** `sealing.seal(payload, header)` semnează și criptează (AES-256-GCM, antetul ca AAD);
  `sealing.open(blob, header)` aruncă `SealError("bad_signature")` la orice problemă. **Retrimiterea** (`replay`)
  o detectează backend-ul: (`direction`, `seq`) e unic în tabelul de pachete.
- **Jurnalul de acces:** `hash = SHA-256(prev_hash + JSON canonic al intrării)`, primele 16 caractere
  (`access_log.entry_hash`).

### Medicul AI

- Frontend → backend: întrebarea, `crew_id`, opțional `alert_id` și istoricul scurt (`POST /ai/chat`).
- Backend → serviciul AI: întrebarea + contextul construit de backend (alerta, dovezile, recomandarea din catalog),
  **fără nume și fără `crew_id`**. Forma exactă: `contract/ai/README.md`.
- **Frontend-ul nu trimite date medicale în `message`** și nu apelează niciodată serviciul AI direct.
- AI-ul nu schimbă niciodată nivelul unei alerte. Dacă nu răspunde în 20 de secunde, backend-ul întoarce textul
  din catalog, cu `fallback = true`.

## 9. Cum schimbăm contractul

Contractul se schimbă în timpul hackathonului. Regulile care ne feresc de integrări stricate:

1. **Se poate oricând, fără anunț:** un câmp nou **opțional** într-un răspuns; un endpoint nou.
2. **Se anunță în chatul echipei înainte:** un câmp nou obligatoriu într-o cerere; o valoare nouă într-o enumerare.
3. **Se evită.** Dacă nu se poate, se face împreună cu cineva de la frontend: redenumirea sau ștergerea unui câmp;
   schimbarea unei căi; schimbarea tipului unui câmp.

Pașii, de fiecare dată (din rădăcina repo-ului):

1. Modifică `backend/app/schemas.py` (și routerul, dacă e cazul).
2. Dacă e endpoint nou, adaugă o cerere de exemplu în `scripts/request_examples.py`.
3. `uv run --project backend python scripts/smoke.py` → trebuie să treacă.
4. `uv run --project backend python scripts/build_docs.py` → regenerează `contract/`.
5. `bash scripts/gen_types.sh` → regenerează `frontend/src/lib/shadow-api.d.ts`.
6. Un singur PR cu toate, cu titlul care începe cu `contract:`.

Contractele interne se schimbă la fel: `ai/service/schemas.py` + copia din `backend/app/ai_schemas.py` (același
PR), semnăturile din `backend/app/security/`, modelele din `backend/app/datafiles.py`.

## 10. Frontend: tipuri și client

Tipurile TypeScript se generează din contract, nu se scriu de mână:

```bash
npm i openapi-fetch @microsoft/fetch-event-source
npm i -D openapi-typescript typescript@5.9
```

```json
{ "scripts": { "api:types": "openapi-typescript ../contract/api/openapi.json -o src/lib/shadow-api.d.ts" } }
```

(Același lucru face `bash scripts/gen_types.sh` din rădăcina repo-ului.)

> `openapi-typescript` 7 are nevoie de TypeScript 5.x. Cu o versiune mai nouă, generatorul se oprește cu eroarea
> `createKeywordTypeNode`; soluția e `npm i -D typescript@5.9`.

`frontend/src/lib/shadow-api.d.ts` e deja generat, iar `frontend/src/lib/api.ts` e clientul: tipizat, cu
autentificare, abonare la evenimente și colectorul de tastare:

```ts
import { client, listAccounts, login, logout, subscribe, createKeystrokeCollector } from "@/lib/api";

// 1. ecranul „Cine ești?” + autentificare cu contul ales (tokenul rămâne în memorie)
const accounts = await listAccounts();                 // câte o casetă pe astronaut
const user = await login("specialist2", password);     // parola scrisă de utilizator

// 2. orice apel e verificat de TypeScript față de contract
const { data: dash } = await client.GET("/api/v1/crew/{crew_id}/dashboard", {
  params: { path: { crew_id: user.crew_id! } },
});

await client.POST("/api/v1/crew/{crew_id}/checkins", {
  params: { path: { crew_id: user.crew_id! } },
  body: { mood: 4, sleep_hours: 5.5 },
});

// 3. evenimente live
const stop = subscribe(
  (ev) => {
    if (ev.type === "alert.created" || ev.type === "dashboard.changed") refreshDashboard();
    if (ev.type === "radiation.alert") showShelterBanner(ev.data);
  },
  () => refreshDashboard(), // după o reconectare
);

// 4. tastare: doar timpi, fără conținut; se leagă de contul autentificat
const ks = createKeystrokeCollector(user.crew_id!, "free_typing", (r) => setLiveBars(r));
// <textarea onKeyDown={ks.onKeyDown} onKeyUp={ks.onKeyUp} />

// 5. schimbarea astronautului: oprește tot, apoi înapoi la „Cine ești?”
await ks.stop();
stop();
await logout();        // șterge și tokenul din memorie
clearAllLoadedData();  // starea React / cache-ul de cereri
```

Erorile: la orice răspuns 4xx/5xx, clientul aruncă `ApiError`, cu `status`, `code` și `message` (în română).

Sfaturi:

- Adresa backend-ului vine din `NEXT_PUBLIC_API_URL` (implicit `http://localhost:8000`).
- Păstrați tokenul în memorie (stare React), nu în `localStorage`. La reîncărcarea paginii, utilizatorul se
  autentifică din nou; pe o stație de lucru folosită de mai mulți oameni, asta e comportamentul dorit.
- Construiți formularul de check-in din `GET /checkin/schema`, ca textele să rămână într-un singur loc.
- Nu calculați statusuri în frontend. Backend-ul trimite `status`; frontend-ul doar îl colorează.

---

## 11. Referința endpoint-urilor

Generată din cod. Exemplele sunt **răspunsuri reale ale backend-ului**, pe scenariul zilei 96; listele lungi sunt scurtate.

- [0. Server health](#0-server-health)
- [1. Authentication](#1-authentication)
- [2. Mission, environment, clock](#2-mission-environment-clock)
- [3. Crew and the interactive body](#3-crew-and-the-interactive-body)
- [4. Check-in](#4-check-in)
- [5. Typing and reaction test](#5-typing-and-reaction-test)
- [6. Exercise](#6-exercise)
- [7. Alerts, triage, catalog](#7-alerts-triage-catalog)
- [8. Link with Earth](#8-link-with-earth)
- [9. Radiation and the solar storm](#9-radiation-and-the-solar-storm)
- [10. AI doctor](#10-ai-doctor)
- [11. Security and evidence](#11-security-and-evidence)
- [12. Demo and simulator](#12-demo-and-simulator)
- [13. Live events (SSE)](#13-live-events-sse)

### 0. Server health

#### `GET /health` — Is the server up?

**Cine poate apela:** oricine, fără autentificare

No authentication. Used by Docker Compose and by the frontend at startup.
`mode` is `mock` while some endpoints still serve example data, then `real`.
`db` is `ok` when the database answers a `SELECT 1`.

**Răspuns 200:** flux `text/event-stream`

<details><summary>Exemplu (autentificat ca <code>nimeni</code>)</summary>

```http
GET /health
```

Răspuns `200`:

```json
{
  "ok": true,
  "version": "1.2.0",
  "mode": "real",
  "db": "ok"
}
```

</details>

---

### 1. Authentication

#### `GET /api/v1/auth/accounts` — Accounts shown on the sign-in screen

**Cine poate apela:** fără autentificare

The list of accounts for the "Who are you?" screen. **No authentication** and no medical data at all: only
names, initials and role.

Frontend: show one tile per account with `location = "ship"` on the onboard workstation and only the account
with `location = "earth"` on the Mission Control screen. On click, ask for that account's password.

**Răspuns 200:** listă de [LoginAccount](#loginaccount)

<details><summary>Exemplu (autentificat ca <code>nimeni</code>)</summary>

```http
GET /api/v1/auth/accounts
```

Răspuns `200`:

```json
[
  {
    "username": "comandant",
    "display_name": "Commander",
    "initials": "CD",
    "role": "astronaut",
    "crew_id": "cm-1",
    "location": "ship"
  },
  {
    "username": "specialist2",
    "display_name": "Mission Specialist 2",
    "initials": "S2",
    "role": "astronaut",
    "crew_id": "cm-2",
    "location": "ship"
  },
  "… încă 3 elemente de același fel"
]
```

</details>

---

#### `POST /api/v1/auth/login` — Sign in (one account per astronaut)

**Cine poate apela:** fără autentificare

**Every astronaut has their own account and password.** There is no shared crew account: the token is bound
to a single `crew_id`, and all data (baseline, typing, check-in, alerts) is linked to it.

Test accounts are in the README, section 1; test passwords are in the seed file.

* Wrong password → `401 invalid_credentials`. The message is the same when the user does not exist.
* 5 wrong passwords on the same account within 5 minutes → `429 too_many_attempts`; the account unlocks by
  itself after 60 real seconds. `details.retry_after_s` says how long is left.
* Every sign-in, successful or not, is written to the access log (`login` / `login_failed`).

Frontend: keep `access_token` in memory (not in `localStorage`) and send it in the
`Authorization: Bearer <token>` header. `user.role` decides the screen: `astronaut` → the interactive body,
`cmo` → the crew medical officer's queue, `earth` → Mission Control.

**Corpul cererii:** [LoginRequest](#loginrequest)

**Răspuns 200:** [LoginResponse](#loginresponse)

**Erori posibile:** 401, 422, 429 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>nimeni</code>)</summary>

```http
POST /api/v1/auth/login
```

Cerere:

```json
{
  "username": "specialist2",
  "password": "cm2-shadow"
}
```

Răspuns `200`:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs…",
  "token_type": "bearer",
  "expires_in": 43200,
  "user": {
    "id": "u-cm-2",
    "username": "specialist2",
    "display_name": "Mission Specialist 2",
    "initials": "S2",
    "role": "astronaut",
    "crew_id": "cm-2"
  }
}
```

</details>

---

#### `GET /api/v1/auth/me` — Who am I

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Returns the account from the token. Useful after a page reload and to always show, visibly, who is signed in.

**Răspuns 200:** [User](#user)

**Erori posibile:** 401, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/auth/me
```

Răspuns `200`:

```json
{
  "id": "u-cm-2",
  "username": "specialist2",
  "display_name": "Mission Specialist 2",
  "initials": "S2",
  "role": "astronaut",
  "crew_id": "cm-2"
}
```

</details>

---

#### `POST /api/v1/auth/logout` — Sign out (switching astronaut)

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Invalidates the current token (the backend puts its `jti` on the revoked-token list). Written to the access
log (`logout`).

**Switching astronaut on the same workstation:** `logout` → delete the token and ALL loaded data from memory →
close the `/events` connection → the "Who are you?" screen → `login` with another account → open `/events`
again. The typing collector stops on sign-out, so keystrokes never reach another astronaut.

Mock tokens (`mock-<username>`) stay valid after logout.

**Răspuns 200:** [Ok](#ok)

**Erori posibile:** 401, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
POST /api/v1/auth/logout
```

Răspuns `200`:

```json
{
  "ok": true
}
```

</details>

---

### 2. Mission, environment, clock

#### `GET /api/v1/mission` — Mission state

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Mission time (SimClock), current day, environment and the state of the link with Earth.

The mission starts on **day 96 at 07:00** (days 1–95 are history generated when the server starts), with time
sped up `time_scale` times (default ×60: one mission day = 24 real minutes).

Call it once at startup. After that, the time comes through SSE (`mission.tick`), not through polling.

**Răspuns 200:** [MissionState](#missionstate)

**Erori posibile:** 401, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/mission
```

Răspuns `200`:

```json
{
  "name": "SHADOW-1",
  "sim_now": "2027-04-15T07:02:28.627293Z",
  "mission_day": 96,
  "total_days": 140,
  "time_scale": 60.0,
  "environment": {
    "id": "mars_transit",
    "name": "Transit to Mars",
    "one_way_delay_s": 700.0,
    "gravity_g": 0.0,
    "baseline_dose_usv_h": 65.8,
    "emphasized_hazards": [
      "radiation",
      "distance",
      "… încă 1 elemente de același fel"
    ],
    "description": "A 3–22 minute delay; levels 1 and 2 handle almost everything on board."
  },
  "link": {
    "environment": "mars_transit",
    "one_way_delay_s": 700.0,
    "one_way_delay_real_s": 11.67,
    "window_open": true,
    "window_closes_at": null,
    "next_window_at": null,
    "queued_down": 0,
    "queued_up": 0
  }
}
```

</details>

---

#### `GET /api/v1/environments` — List of environments

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

The 4 environments for the switch: station, Moon, transit to Mars, base on Mars.

**Răspuns 200:** listă de [EnvironmentInfo](#environmentinfo)

**Erori posibile:** 401, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/environments
```

Răspuns `200`:

```json
[
  {
    "id": "iss",
    "name": "Space station (low Earth orbit)",
    "one_way_delay_s": 1.0,
    "gravity_g": 0.0,
    "baseline_dose_usv_h": 30.5,
    "emphasized_hazards": [
      "gravity",
      "hostile_environment"
    ],
    "description": "Earth answers almost immediately; triage escalates to level 3 more readily."
  },
  {
    "id": "moon_base",
    "name": "Moon base",
    "one_way_delay_s": 1.3,
    "gravity_g": 0.165,
    "baseline_dose_usv_h": 57.0,
    "emphasized_hazards": [
      "radiation",
      "gravity"
    ],
    "description": "Reduced gravity, but not zero: different thresholds for bones and the heart."
  },
  "… încă 2 elemente de același fel"
]
```

</details>

---

#### `PUT /api/v1/mission/environment` — Change the environment

**Cine poate apela:** astronaut, ofițer medical (cmo)

The environment switch. Changes the link delay, the background dose rate and the gravity-dependent thresholds.

**Effects:** packets already `in_transit` keep their arrival time; new ones use the new delay.
**SSE:** `environment.changed` with the new `MissionState`.

**Corpul cererii:** [EnvironmentUpdate](#environmentupdate)

**Răspuns 200:** [MissionState](#missionstate)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>medic</code>)</summary>

```http
PUT /api/v1/mission/environment
```

Cerere:

```json
{
  "environment": "mars_transit"
}
```

Răspuns `200`:

```json
{
  "name": "SHADOW-1",
  "sim_now": "2027-04-15T07:02:29.121022Z",
  "mission_day": 96,
  "total_days": 140,
  "time_scale": 60.0,
  "environment": {
    "id": "mars_transit",
    "name": "Transit to Mars",
    "one_way_delay_s": 700.0,
    "gravity_g": 0.0,
    "baseline_dose_usv_h": 65.8,
    "emphasized_hazards": [
      "radiation",
      "distance",
      "… încă 1 elemente de același fel"
    ],
    "description": "A 3–22 minute delay; levels 1 and 2 handle almost everything on board."
  },
  "link": {
    "environment": "mars_transit",
    "one_way_delay_s": 700.0,
    "one_way_delay_real_s": 11.67,
    "window_open": true,
    "window_closes_at": null,
    "next_window_at": null,
    "queued_down": 0,
    "queued_up": 0
  }
}
```

</details>

---

#### `PUT /api/v1/sim/clock` — Change the clock speed or day (demo)

**Cine poate apela:** astronaut, ofițer medical (cmo)

Demo only.

* `time_scale` changes the speed; the current mission time stays the same.
* `mission_day` jumps **forward** to the start of that day (07:00): the backend generates the missing days with
  the simulator and runs the engine over them, so new alerts can appear. **Going back is not possible** (409
  `invalid_state`); for a rehearsal from the start use `POST /sim/reset`.

The timeline scrubber does NOT use this endpoint: it only reads the history with `?as_of_day=`.

**SSE:** `mission.tick` with the new day, then `dashboard.changed` and possibly `alert.created`.

**Corpul cererii:** [ClockUpdate](#clockupdate)

**Răspuns 200:** [MissionState](#missionstate)

**Erori posibile:** 401, 403, 409, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>medic</code>)</summary>

```http
PUT /api/v1/sim/clock
```

Cerere:

```json
{
  "time_scale": 60
}
```

Răspuns `200`:

```json
{
  "name": "SHADOW-1",
  "sim_now": "2027-04-15T07:02:29.529372Z",
  "mission_day": 96,
  "total_days": 140,
  "time_scale": 60.0,
  "environment": {
    "id": "mars_transit",
    "name": "Transit to Mars",
    "one_way_delay_s": 700.0,
    "gravity_g": 0.0,
    "baseline_dose_usv_h": 65.8,
    "emphasized_hazards": [
      "radiation",
      "distance",
      "… încă 1 elemente de același fel"
    ],
    "description": "A 3–22 minute delay; levels 1 and 2 handle almost everything on board."
  },
  "link": {
    "environment": "mars_transit",
    "one_way_delay_s": 700.0,
    "one_way_delay_real_s": 11.67,
    "window_open": true,
    "window_closes_at": null,
    "next_window_at": null,
    "queued_down": 0,
    "queued_up": 0
  }
}
```

</details>

---

### 3. Crew and the interactive body

#### `GET /api/v1/crew` — Crew list

**Cine poate apela:** ofițer medical (cmo)

For the crew medical officer only. Holds only the overall status, no medical values.

**Răspuns 200:** listă de [CrewSummary](#crewsummary)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>medic</code>)</summary>

```http
GET /api/v1/crew
```

Răspuns `200`:

```json
[
  {
    "member": {
      "id": "cm-1",
      "display_name": "Commander",
      "initials": "CD",
      "role_title": "Commander",
      "is_cmo": false
    },
    "overall_status": "ok",
    "active_alerts": 0,
    "highest_level": null
  },
  {
    "member": {
      "id": "cm-2",
      "display_name": "Mission Specialist 2",
      "initials": "S2",
      "role_title": "Mission Specialist",
      "is_cmo": false
    },
    "overall_status": "alert",
    "active_alerts": 2,
    "highest_level": 2
  },
  "… încă 2 elemente de același fel"
]
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/dashboard` — The astronaut's dashboard

**Cine poate apela:** astronaut, ofițer medical (cmo)

**The main call of the astronaut's screen.** In one response: the state of the 4 pillars (the colours of the
body zones), the perception gap, the cross signals, the main alert, the streaks and the reminders.

Reload it when you get SSE `dashboard.changed`, `alert.created` or `alert.updated`.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |
| `as_of_day` | query | număr întreg \| null | nu | Timeline scrubber: the state at the end of this day. Without it = now. Must be ≤ the current day (future days do not exist yet) → otherwise 422. (min 1) |

**Răspuns 200:** [Dashboard](#dashboard)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/crew/cm-2/dashboard
```

Răspuns `200`:

```json
{
  "crew": {
    "id": "cm-2",
    "display_name": "Mission Specialist 2",
    "initials": "S2",
    "role_title": "Mission Specialist",
    "is_cmo": false
  },
  "as_of": "2027-04-15T07:02:31.988957Z",
  "mission_day": 96,
  "overall_status": "alert",
  "pillars": [
    {
      "pillar": "behavioral",
      "name": "Typing",
      "body_zone": "brain",
      "status": "watch",
      "score": 27.6,
      "headline": "Typing 18% slower than usual",
      "hazard": "isolation",
      "active_alert_id": "al-0006"
    },
    {
      "pillar": "cardio",
      "name": "Heart",
      "body_zone": "heart",
      "status": "ok",
      "score": 99.2,
      "headline": "Within your in-flight range",
      "hazard": "gravity",
      "active_alert_id": null
    },
    "… încă 2 elemente de același fel"
  ],
  "perception_gap": {
    "self_reported_mood": null,
    "self_score": null,
    "objective_score": 53.5,
    "gap": null,
    "status": "unknown",
    "explanation": "Not enough data yet to compare how you feel with your objective data.",
    "contributing_signals": [
      "Typing: -18% speed",
      "Night pulse: +7.0 bpm",
      "… încă 1 elemente de același fel"
    ]
  },
  "cross_signals": [
    {
      "id": "xs-cm-2-96",
      "title": "Possible onset of an illness",
      "pillars": [
        "behavioral",
        "immune"
      ],
      "signals": [
        "Night pulse: +7.0 bpm",
        "Temperature: +0.4 °C",
        "… încă 2 elemente de același fel"
      ],
      "confidence": 0.8,
      "explanation": "4 weak, independent signals from 2 pillars point the same way. Each one alone is not an alert; together they weigh more."
    }
  ],
  "alerts_active_count": 2,
  "top_alert": {
    "id": "al-0005",
    "crew_id": "cm-2",
    "topic": "immune",
    "level": 2,
    "status": "alert",
    "state": "escalated",
    "title": "Night pulse +7 bpm, 3 nights in a row",
    "created_at": "2027-04-13T07:00:00Z"
  },
  "streaks": [
    {
      "key": "checkin",
      "label": "Daily check-in",
      "days": 95,
      "best": 95
    },
    {
      "key": "split_training",
      "label": "Training in two sessions",
      "days": 33,
      "best": 60
    },
    "… încă 1 elemente de același fel"
  ],
  "reminders": [
    {
      "id": "rm-1",
      "kind": "checkin",
      "label": "Morning check-in",
      "due_at": "2027-04-15T07:00:00Z",
      "done": false,
      "overdue": true
    },
    {
      "id": "rm-2",
      "kind": "pvt",
      "label": "Reaction test (3 minutes)",
      "due_at": "2027-04-15T09:00:00Z",
      "done": false,
      "overdue": false
    },
    "… încă 1 elemente de același fel"
  ],
  "radiation_alert_active": false,
  "checkin_done_today": false
}
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/pillars/{pillar}` — The panel of a body zone

**Cine poate apela:** astronaut, ofițer medical (cmo)

Called on a click on a zone. Holds, in display order: the function of the body part, the space hazard,
the values against the baseline, the chart, the explanation, the action plan and the sources.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |
| `pillar` | cale | [Pillar](#pillar) | da |  |
| `as_of_day` | query | număr întreg \| null | nu | Timeline scrubber: the state at the end of this day. Without it = now. Must be ≤ the current day (future days do not exist yet) → otherwise 422. (min 1) |

**Răspuns 200:** [PillarDetail](#pillardetail)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/crew/cm-2/pillars/immune
```

Răspuns `200`:

```json
{
  "pillar": "immune",
  "name": "Sentinel",
  "body_zone": "immune",
  "function_text": "The immune system defends the body against viruses, bacteria and abnormal cells. In flight, stress, disrupted sleep and radiation throw it off balance.",
  "hazard": "hostile_environment",
  "hazard_text": "Radiation and the closed environment: stress and shared space weaken the body's defences.",
  "status": "alert",
  "score": 58.0,
  "explanation": "Your night pulse has been at least 4 bpm above your personal median (53.9 bpm) for 3 nights in a row. In the NightSignal study this pattern often came before symptoms of an infection. Tell the crew medical officer.",
  "metrics": [
    {
      "key": "night_pulse_bpm",
      "label": "Night pulse",
      "value": 60.9,
      "unit": "bpm",
      "baseline": 53.9,
      "deviation_abs": 7.0,
      "deviation_pct": 13.0,
      "status": "alert",
      "source": "simulated",
      "measured_at": "2027-04-15T03:00:00Z"
    },
    {
      "key": "temperature_c",
      "label": "Temperature",
      "value": 37.3,
      "unit": "°C",
      "baseline": 36.9,
      "deviation_abs": 0.4,
      "deviation_pct": 1.1,
      "status": "watch",
      "source": "simulated",
      "measured_at": "2027-04-15T07:00:00Z"
    },
    "… încă 2 elemente de același fel"
  ],
  "chart": {
    "metric_key": "night_pulse_bpm",
    "label": "Night pulse",
    "unit": "bpm",
    "baseline": 53.9,
    "band_low": 52.4,
    "band_high": 55.4,
    "threshold": 57.9,
    "threshold_label": "+4 bpm, 2 nights (NightSignal)",
    "points": [
      {
        "day": 87,
        "t": "2027-04-06T03:00:00Z",
        "value": 53.4,
        "status": "ok"
      },
      {
        "day": 88,
        "t": "2027-04-07T03:00:00Z",
        "value": 53.8,
        "status": "ok"
      },
      "… încă 8 elemente de același fel"
    ]
  },
  "plan_steps": [
    {
      "id": "st-1",
      "text": "Go to bed an hour earlier for the next 3 nights.",
      "done": false,
      "done_at": null
    },
    {
      "id": "st-2",
      "text": "Take your temperature morning and evening.",
      "done": false,
      "done_at": null
    },
    "… încă 1 elemente de același fel"
  ],
  "active_alert_id": "al-0005",
  "recheck_at": "2027-04-16T07:00:00Z",
  "sources": [
    {
      "citation": "Alavi et al. (2022), Real-time alerting system for COVID-19 and other stress events using wearable data, Nature Medicine 28:175–184",
      "url": "https://www.nature.com/articles/s41591-021-01593-2",
      "verification": "verified",
      "derivation": "published",
      "evidence_strength": "moderate"
    },
    {
      "citation": "Rooney et al. (2019), Herpes Virus Reactivation in Astronauts During Spaceflight, Frontiers in Microbiology 10:16",
      "url": "https://www.frontiersin.org/articles/10.3389/fmicb.2019.00016/full",
      "verification": "verified",
      "derivation": "published",
      "evidence_strength": "moderate"
    },
    "… încă 1 elemente de același fel"
  ],
  "limits_text": "The algorithm cannot tell the type of infection and can give false alarms. It was validated on civilians, not on astronauts.",
  "data_is_simulated": true
}
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/pillars/{pillar}/series` — The series of a metric (chart)

**Cine poate apela:** astronaut, ofițer medical (cmo)

For a second chart or for a longer interval than the panel's (which has the last 10 days).

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |
| `pillar` | cale | [Pillar](#pillar) | da |  |
| `metric` | query | text | da | The metric key, e.g. `night_pulse_bpm`. See README, “Metric keys”. |
| `from_day` | query | număr întreg | nu |  Implicit: `1`. (min 1) |
| `to_day` | query | număr întreg \| null | nu | Default: the current day. (min 1) |

**Răspuns 200:** [MetricSeries](#metricseries)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/crew/cm-2/pillars/immune/series?metric=night_pulse_bpm&from_day=87
```

Răspuns `200`:

```json
{
  "metric_key": "night_pulse_bpm",
  "label": "Night pulse",
  "unit": "bpm",
  "baseline": 53.9,
  "band_low": 52.4,
  "band_high": 55.4,
  "threshold": 57.9,
  "threshold_label": "+4 bpm, 2 nights (NightSignal)",
  "points": [
    {
      "day": 87,
      "t": "2027-04-06T03:00:00Z",
      "value": 53.4,
      "status": "ok"
    },
    {
      "day": 88,
      "t": "2027-04-07T03:00:00Z",
      "value": 53.8,
      "status": "ok"
    },
    "… încă 8 elemente de același fel"
  ]
}
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/timeline` — History by day (timeline scrubber)

**Cine poate apela:** astronaut, ofițer medical (cmo)

The state of every pillar on every day **that has happened**: from `from_day` to the current day (the
mission starts on day 96, so at first there are 96 days). Future days are not included; the scrubber shows the
rest up to `total_days` (from `/mission`) as "not yet".

Load it once at startup and reload it on `mission.tick` only when `mission_day` changes.
When the user stops on a day, reload `dashboard` and the open panel with `?as_of_day=`.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |
| `from_day` | query | număr întreg | nu |  Implicit: `1`. (min 1) |
| `to_day` | query | număr întreg \| null | nu | Default and maximum: the current day. (min 1) |

**Răspuns 200:** [Timeline](#timeline)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/crew/cm-2/timeline?from_day=94
```

Răspuns `200`:

```json
{
  "crew_id": "cm-2",
  "from_day": 94,
  "to_day": 96,
  "days": [
    {
      "day": 94,
      "date": "2027-04-13T00:00:00Z",
      "overall_status": "watch",
      "pillars": {
        "behavioral": "ok",
        "cardio": "ok",
        "immune": "watch",
        "musculoskeletal": "ok"
      },
      "events": [
        "Sentinel alert"
      ]
    },
    {
      "day": 95,
      "date": "2027-04-14T00:00:00Z",
      "overall_status": "alert",
      "pillars": {
        "behavioral": "watch",
        "cardio": "ok",
        "immune": "alert",
        "musculoskeletal": "ok"
      },
      "events": [
        "Typing alert",
        "Sentinel alert escalated"
      ]
    },
    "… încă 1 elemente de același fel"
  ]
}
```

</details>

---

### 4. Check-in

#### `GET /api/v1/checkin/schema` — Check-in fields

**Cine poate apela:** astronaut, ofițer medical (cmo)

The list of fields, with the "How to measure", "What it means" and "Why it matters in space" texts and the
plausibility limits (`min`/`max`). The frontend builds the form from this response; do not keep the texts in code.

**Răspuns 200:** [CheckinSchema](#checkinschema)

**Erori posibile:** 401, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/checkin/schema
```

Răspuns `200`:

```json
{
  "indicators": [
    {
      "key": "mood",
      "label": "Mood",
      "unit": "",
      "input": "scale_1_5",
      "min": 1.0,
      "max": 5.0,
      "step": 1.0,
      "choices": null,
      "required": true,
      "how_to_measure": "Choose from 1 (very bad) to 5 (very good).",
      "what_it_means": "How you feel; it feeds the perception gap.",
      "why_in_space": "Isolation and distance from Earth weigh on behavioural health.",
      "pillar": "behavioral",
      "source": {
        "citation": "NASA HRP — Risk of Adverse Cognitive or Behavioral Changes and Psychiatric Disorders",
        "url": "https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=99",
        "verification": "verified",
        "derivation": "published",
        "evidence_strength": "strong"
      }
    },
    {
      "key": "systolic_mmhg",
      "label": "Blood pressure (systolic)",
      "unit": "mmHg",
      "input": "number",
      "min": 60.0,
      "max": 250.0,
      "step": 1.0,
      "choices": null,
      "required": false,
      "how_to_measure": "With the cuff, at rest, after a few minutes sitting down.",
      "what_it_means": "The pressure of blood on the arteries; we follow it as a trend against your normal.",
      "why_in_space": "In microgravity, fluids shift towards the head, and blood pressure is usually lower than on Earth.",
      "pillar": "cardio",
      "source": {
        "citation": "NASA HRP — Risk of Cardiovascular Adaptations",
        "url": "https://www.nasa.gov/reference/risk-of-cardiovascular-adaptations/",
        "verification": "unverified",
        "derivation": "derived",
        "evidence_strength": "weak"
      }
    },
    "… încă 6 elemente de același fel"
  ]
}
```

</details>

---

#### `POST /api/v1/crew/{crew_id}/checkins` — Send the morning check-in

**Cine poate apela:** astronaut, ofițer medical (cmo)

Saves the check-in of the day. **One check-in per mission day**: a second one replaces the first.

What the backend does, in order:
1. checks every field against `min`/`max` from the schema; impossible fields do NOT give a 422 error, they show
   up in `rejected` and are saved as `null` (the rest of the check-in stays valid);
2. compares the values with the personal baseline;
3. recomputes the perception gap;
4. runs triage and creates alerts, if needed;
5. updates the streak.

**SSE:** `dashboard.changed`, plus `alert.created` for every new alert.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |

**Corpul cererii:** [CheckinCreate](#checkincreate)

**Răspuns 201:** [CheckinResult](#checkinresult)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
POST /api/v1/crew/cm-2/checkins
```

Cerere:

```json
{
  "mood": 4,
  "systolic_mmhg": 112,
  "diastolic_mmhg": 72,
  "pulse_bpm": 58,
  "glucose_mg_dl": 92,
  "temperature_c": 41.9,
  "sleep_hours": 5.5,
  "meals_eaten": "some"
}
```

Răspuns `201`:

```json
{
  "checkin": {
    "id": "ck-0381",
    "crew_id": "cm-2",
    "mission_day": 96,
    "created_at": "2027-04-15T07:02:39.372694Z",
    "values": {
      "mood": 4,
      "systolic_mmhg": 112.0,
      "diastolic_mmhg": 72.0,
      "pulse_bpm": 58.0,
      "glucose_mg_dl": 92.0,
      "temperature_c": null,
      "sleep_hours": 5.5,
      "meals_eaten": "some",
      "note": null
    }
  },
  "rejected": [
    {
      "field": "temperature_c",
      "value": 41.9,
      "reason": "implausible",
      "message": "41.9 is outside the possible range (34–41.5). Measure again."
    }
  ],
  "perception_gap": {
    "self_reported_mood": 4,
    "self_score": 80.0,
    "objective_score": 52.7,
    "gap": 27.3,
    "status": "alert",
    "explanation": "You rate yourself 4/5 (80/100), but your objective data score 53/100 only (Typing: -18% speed, Night pulse: +7.0 bpm, Sleep: -1.1 h).",
    "contributing_signals": [
      "Typing: -18% speed",
      "Night pulse: +7.0 bpm",
      "… încă 1 elemente de același fel"
    ]
  },
  "alerts_created": [],
  "streak": {
    "key": "checkin",
    "label": "Daily check-in",
    "days": 96,
    "best": 96
  },
  "message": "Check-in saved. 96 days in a row."
}
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/checkins` — Check-in history

**Cine poate apela:** astronaut, ofițer medical (cmo)

The check-ins in the interval, newest first.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |
| `from_day` | query | număr întreg | nu |  Implicit: `1`. (min 1) |
| `to_day` | query | număr întreg | nu |  Implicit: `140`. (min 1) |

**Răspuns 200:** listă de [Checkin](#checkin)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/crew/cm-2/checkins?from_day=90
```

Răspuns `200`:

```json
[
  {
    "id": "ck-0381",
    "crew_id": "cm-2",
    "mission_day": 96,
    "created_at": "2027-04-15T07:02:39.372694Z",
    "values": {
      "mood": 4,
      "systolic_mmhg": 112.0,
      "diastolic_mmhg": 72.0,
      "pulse_bpm": 58.0,
      "glucose_mg_dl": 92.0,
      "temperature_c": null,
      "sleep_hours": 5.5,
      "meals_eaten": "some",
      "note": null
    }
  },
  {
    "id": "ck-0378",
    "crew_id": "cm-2",
    "mission_day": 95,
    "created_at": "2027-04-14T07:00:00Z",
    "values": {
      "mood": 4,
      "systolic_mmhg": 107.4,
      "diastolic_mmhg": 73.6,
      "pulse_bpm": 57.0,
      "glucose_mg_dl": 90.2,
      "temperature_c": 37.3,
      "sleep_hours": 5.3,
      "meals_eaten": "all",
      "note": null
    }
  },
  "… încă 5 elemente de același fel"
]
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/checkins/today` — Today's check-in

**Cine poate apela:** astronaut, ofițer medical (cmo)

Returns the check-in of the current day, or `null` if it has not been done. Use it to decide whether to show
the form.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |

**Răspuns 200:** [Checkin](#checkin) \| null

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/crew/cm-2/checkins/today
```

Răspuns `200`:

```json
{
  "id": "ck-0381",
  "crew_id": "cm-2",
  "mission_day": 96,
  "created_at": "2027-04-15T07:02:39.372694Z",
  "values": {
    "mood": 4,
    "systolic_mmhg": 112.0,
    "diastolic_mmhg": 72.0,
    "pulse_bpm": 58.0,
    "glucose_mg_dl": 92.0,
    "temperature_c": null,
    "sleep_hours": 5.5,
    "meals_eaten": "some",
    "note": null
  }
}
```

</details>

---

### 5. Typing and reaction test

#### `POST /api/v1/crew/{crew_id}/keystrokes/batches` — Send a batch of key presses

**Cine poate apela:** astronaut, ofițer medical (cmo)

**Privacy: send only the timings and the key class, never the character.** The backend rejects with 422 any
extra field (e.g. `key`, `code`, `text`).

Frontend: collect the `keydown`/`keyup` events and send a batch every ~5 seconds or every 200 keys, with the
same `session_id` while the user keeps typing in the same field. The response holds the cumulative features of
the session, so you can show it directly in the live bars.

The first sessions build the baseline: while `baseline_ready` is `false`, `status` is `unknown`. A session is
judged only after its first 30 keys.

**SSE:** `alert.created` (or `alert.updated`) and `dashboard.changed` when the deviation crosses the threshold.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |

**Corpul cererii:** [KeystrokeBatch](#keystrokebatch)

**Răspuns 200:** [KeystrokeResult](#keystrokeresult)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
POST /api/v1/crew/cm-2/keystrokes/batches
```

Cerere:

```json
{
  "session_id": "8b1f0c1e-6f0a-4f0e-9d53-2c1a7f1b9e10",
  "context": "free_typing",
  "events": [
    {
      "t_down_ms": 10234.5,
      "t_up_ms": 10321.1,
      "key_class": "char"
    },
    {
      "t_down_ms": 10412.0,
      "t_up_ms": 10498.7,
      "key_class": "char"
    },
    {
      "t_down_ms": 10655.3,
      "t_up_ms": 10731.9,
      "key_class": "backspace"
    }
  ]
}
```

Răspuns `200`:

```json
{
  "session_id": "8b1f0c1e-6f0a-4f0e-9d53-2c1a7f1b9e10",
  "features": {
    "hold_ms_mean": 83.3,
    "hold_ms_sd": 4.7,
    "flight_ms_mean": 210.4,
    "flight_ms_sd": 32.9,
    "backspace_rate": 0.333,
    "keys_per_min": 285.2,
    "n_keys": 3
  },
  "baseline": {
    "hold_ms_mean": 95.7,
    "hold_ms_sd": 19.1,
    "flight_ms_mean": 284.7,
    "flight_ms_sd": 99.6,
    "backspace_rate": 0.051,
    "keys_per_min": 210.8,
    "n_keys": 2620
  },
  "deviation_z": {
    "hold_ms_mean": -2.06,
    "keys_per_min": 9.3,
    "flight_ms_mean": -4.95,
    "backspace_rate": 14.11
  },
  "fatigue_index": null,
  "status": "unknown",
  "baseline_ready": true,
  "baseline_sessions": 7
}
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/keystrokes/summary` — Typing summary

**Cine poate apela:** astronaut, ofițer medical (cmo)

The personal baseline, the latest session and the recent sessions. For the "Your rhythm" card and the
comparison in the demo.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |
| `last` | query | număr întreg | nu | How many recent sessions to return. Implicit: `10`. (min 1; max 100) |

**Răspuns 200:** [KeystrokeSummary](#keystrokesummary)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/crew/cm-2/keystrokes/summary?last=6
```

Răspuns `200`:

```json
{
  "baseline": {
    "hold_ms_mean": 95.7,
    "hold_ms_sd": 19.1,
    "flight_ms_mean": 284.7,
    "flight_ms_sd": 99.6,
    "backspace_rate": 0.051,
    "keys_per_min": 210.8,
    "n_keys": 2620
  },
  "current": {
    "hold_ms_mean": 83.3,
    "hold_ms_sd": 4.7,
    "flight_ms_mean": 210.4,
    "flight_ms_sd": 32.9,
    "backspace_rate": 0.333,
    "keys_per_min": 285.2,
    "n_keys": 3
  },
  "fatigue_index": null,
  "status": "unknown",
  "baseline_ready": true,
  "sessions": [
    {
      "session_id": "sim-cm-2-d091",
      "at": "2027-04-10T07:15:00Z",
      "keys_per_min": 214.6,
      "hold_ms_mean": 95.8,
      "fatigue_index": 0.2,
      "status": "ok"
    },
    {
      "session_id": "sim-cm-2-d092",
      "at": "2027-04-11T07:15:00Z",
      "keys_per_min": 218.5,
      "hold_ms_mean": 94.6,
      "fatigue_index": 0.0,
      "status": "ok"
    },
    "… încă 4 elemente de același fel"
  ]
}
```

</details>

---

#### `POST /api/v1/crew/{crew_id}/pvt` — Send a reaction test (PVT-B)

**Cine poate apela:** astronaut, ofițer medical (cmo)

The 3-minute test runs entirely in the frontend; send all the trials here at the end.

The backend computes the mean 1/RT, the lapses (RT ≥ 355 ms) and the deviation from the baseline. The first
3 tests are practice and do not enter the baseline (`status = unknown`).

**SSE:** `dashboard.changed`, plus `alert.created` / `alert.updated` when the speed drops past the threshold.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |

**Corpul cererii:** [PvtSubmit](#pvtsubmit)

**Răspuns 201:** [PvtResult](#pvtresult)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
POST /api/v1/crew/cm-2/pvt
```

Cerere:

```json
{
  "started_at": "2027-04-15T09:00:00Z",
  "duration_s": 180,
  "trials": [
    {
      "stimulus_at_ms": 3200,
      "rt_ms": 287,
      "false_start": false
    },
    {
      "stimulus_at_ms": 8900,
      "rt_ms": 402,
      "false_start": false
    },
    {
      "stimulus_at_ms": 14100,
      "rt_ms": null,
      "false_start": true
    }
  ]
}
```

Răspuns `201`:

```json
{
  "id": "pvt-0001",
  "crew_id": "cm-2",
  "at": "2027-04-15T07:02:47.197635Z",
  "n_trials": 3,
  "mean_rt_ms": 344.5,
  "mean_speed": 2.986,
  "lapses": 1,
  "false_starts": 1,
  "baseline_speed": null,
  "deviation_sd": null,
  "status": "unknown"
}
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/pvt` — Reaction test history

**Cine poate apela:** astronaut, ofițer medical (cmo)

The reaction tests, newest first.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |
| `limit` | query | număr întreg | nu |  Implicit: `20`. (min 1; max 200) |

**Răspuns 200:** listă de [PvtResult](#pvtresult)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/crew/cm-2/pvt
```

Răspuns `200`:

```json
[
  {
    "id": "pvt-0001",
    "crew_id": "cm-2",
    "at": "2027-04-15T07:02:47.197635Z",
    "n_trials": 3,
    "mean_rt_ms": 344.5,
    "mean_speed": 2.986,
    "lapses": 1,
    "false_starts": 1,
    "baseline_speed": null,
    "deviation_sd": null,
    "status": "unknown"
  }
]
```

</details>

---

### 6. Exercise

#### `GET /api/v1/crew/{crew_id}/exercise/today` — Today's exercise plan

**Cine poate apela:** astronaut, ofițer medical (cmo)

The planned and completed sessions, the loading score, the recommendation to split into two sessions, the
streak and the bone projection (an estimate).

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |

**Răspuns 200:** [ExerciseToday](#exercisetoday)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/crew/cm-2/exercise/today
```

Răspuns `200`:

```json
{
  "mission_day": 96,
  "planned_sessions": 2,
  "completed_sessions": 0,
  "loading_score": 0.0,
  "loading_target": 80.0,
  "split_recommended": true,
  "recommendation_text": "Plan two sessions today, a few hours apart: it helps your bones more than one long session.",
  "streak": {
    "key": "split_training",
    "label": "Training in two sessions",
    "days": 33,
    "best": 60
  },
  "sessions": [],
  "projection": {
    "current_plan_pct_month": -0.45,
    "split_plan_pct_month": -0.45,
    "note": "Estimate, not a measurement: bone density cannot be measured on board. The benefit of splitting the training is shown only in animals (Robling 2002)."
  }
}
```

</details>

---

#### `POST /api/v1/crew/{crew_id}/exercise/sessions` — Log an exercise session

**Cine poate apela:** astronaut, ofițer medical (cmo)

In the real version the log comes from the device. In the prototype the simulator or the astronaut sends it.

**SSE:** `dashboard.changed`.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |

**Corpul cererii:** [ExerciseSessionCreate](#exercisesessioncreate)

**Răspuns 201:** [ExerciseSession](#exercisesession)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
POST /api/v1/crew/cm-2/exercise/sessions
```

Cerere:

```json
{
  "kind": "resistance",
  "started_at": "2027-04-15T16:00:00Z",
  "duration_min": 35,
  "sets": [
    {
      "exercise": "genuflexiuni ARED",
      "reps": 10,
      "load_kg": 85
    }
  ]
}
```

Răspuns `201`:

```json
{
  "kind": "resistance",
  "started_at": "2027-04-15T16:00:00Z",
  "duration_min": 35.0,
  "sets": [
    {
      "exercise": "genuflexiuni ARED",
      "reps": 10,
      "load_kg": 85.0
    }
  ],
  "id": "ex-0757",
  "crew_id": "cm-2",
  "mission_day": 96,
  "loading_score": 11.8,
  "source": "manual"
}
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/exercise/sessions` — Session history

**Cine poate apela:** astronaut, ofițer medical (cmo)

The sessions in the interval, newest first.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |
| `from_day` | query | număr întreg | nu |  Implicit: `1`. (min 1) |
| `to_day` | query | număr întreg | nu |  Implicit: `140`. (min 1) |

**Răspuns 200:** listă de [ExerciseSession](#exercisesession)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/crew/cm-2/exercise/sessions?from_day=90
```

Răspuns `200`:

```json
[
  {
    "kind": "resistance",
    "started_at": "2027-04-15T16:00:00Z",
    "duration_min": 35.0,
    "sets": [
      {
        "exercise": "genuflexiuni ARED",
        "reps": 10,
        "load_kg": 85.0
      }
    ],
    "id": "ex-0757",
    "crew_id": "cm-2",
    "mission_day": 96,
    "loading_score": 11.8,
    "source": "manual"
  },
  {
    "kind": "resistance",
    "started_at": "2027-04-14T16:00:00Z",
    "duration_min": 40.0,
    "sets": [
      {
        "exercise": "ARED squat",
        "reps": 10,
        "load_kg": 78.3
      },
      {
        "exercise": "ARED deadlift",
        "reps": 10,
        "load_kg": 79.4
      },
      "… încă 1 elemente de același fel"
    ],
    "id": "ex-0752",
    "crew_id": "cm-2",
    "mission_day": 95,
    "loading_score": 32.7,
    "source": "simulated"
  },
  "… încă 11 elemente de același fel"
]
```

</details>

---

### 7. Alerts, triage, catalog

#### `GET /api/v1/crew/{crew_id}/alerts` — A crew member's alerts

**Cine poate apela:** astronaut, ofițer medical (cmo)

Short list, most severe first. The crew medical officer only gets level ≥ 2 alerts of other members here.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |
| `state` | query | [AlertState](#alertstate) \| null | nu | Filter. Without it = all unresolved alerts. |
| `topic` | query | [AlertTopic](#alerttopic) \| null | nu |  |

**Răspuns 200:** listă de [AlertBrief](#alertbrief)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/crew/cm-2/alerts
```

Răspuns `200`:

```json
[
  {
    "id": "al-0005",
    "crew_id": "cm-2",
    "topic": "immune",
    "level": 2,
    "status": "alert",
    "state": "escalated",
    "title": "Night pulse +7 bpm, 3 nights in a row",
    "created_at": "2027-04-13T07:00:00Z"
  },
  {
    "id": "al-0006",
    "crew_id": "cm-2",
    "topic": "behavioral",
    "level": 1,
    "status": "watch",
    "state": "active",
    "title": "Typing 18% slower than usual",
    "created_at": "2027-04-14T07:17:08.050896Z"
  }
]
```

</details>

---

#### `GET /api/v1/cmo/queue` — Crew medical officer's queue

**Cine poate apela:** ofițer medical (cmo)

All unresolved level 2 and 3 alerts across the crew. The main screen of the `cmo` role.

**Răspuns 200:** listă de [AlertBrief](#alertbrief)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>medic</code>)</summary>

```http
GET /api/v1/cmo/queue
```

Răspuns `200`:

```json
[
  {
    "id": "al-0005",
    "crew_id": "cm-2",
    "topic": "immune",
    "level": 2,
    "status": "alert",
    "state": "escalated",
    "title": "Night pulse +7 bpm, 3 nights in a row",
    "created_at": "2027-04-13T07:00:00Z"
  }
]
```

</details>

---

#### `GET /api/v1/alerts/{alert_id}` — Full alert

**Cine poate apela:** astronaut, ofițer medical (cmo)

The evidence, the cause (individual or environmental), the catalog recommendation with its source, the action
plan, the recheck date and the history. Every read by the crew medical officer is written to the access log.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `alert_id` | cale | text | da |  |

**Răspuns 200:** [Alert](#alert)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/alerts/al-0005
```

Răspuns `200`:

```json
{
  "id": "al-0005",
  "crew_id": "cm-2",
  "topic": "immune",
  "level": 2,
  "status": "alert",
  "state": "escalated",
  "title": "Night pulse +7 bpm, 3 nights in a row",
  "created_at": "2027-04-13T07:00:00Z",
  "explanation": "Your night pulse has been at least 4 bpm above your personal median (53.9 bpm) for 3 nights in a row. In the NightSignal study this pattern often came before symptoms of an infection. Tell the crew medical officer.",
  "cause": "individual",
  "cause_explanation": "Only you have this deviation; the rest of the crew is within their usual range.",
  "evidence": [
    {
      "metric_key": "night_pulse_bpm",
      "label": "Night pulse",
      "value": 60.9,
      "unit": "bpm",
      "baseline": 53.9,
      "deviation_text": "+7.0 bpm above your personal median, 3 nights in a row"
    },
    {
      "metric_key": "temperature_c",
      "label": "Temperature",
      "value": 37.3,
      "unit": "°C",
      "baseline": 36.9,
      "deviation_text": "+0.4 °C vs your in-flight median"
    },
    "… încă 1 elemente de același fel"
  ],
  "recommendation": {
    "id": "immune-2-1",
    "topic": "immune",
    "level": 2,
    "trigger": "NightSignal red alert: mean night-time heart rate ≥ +4 bpm above your personal median two nights in a row, especially if skin temperature exceeds the derived SHADOW threshold or symptoms appear.",
    "action": "Notify the crew medical officer (CMO) with the heart rate and temperature chart against your baseline and your symptom journal. Only the CMO decides on assessment or treatment; the app does not recommend medicines.",
    "hrp_risk": "Risk of In Mission Impacts, Adverse Health Events or Long-Term Health Impacts due to Altered Immune Response",
    "hrp_risk_url": "https://humanresearchroadmap.nasa.gov/Risks/?i=85",
    "source": {
      "citation": "Alavi A, Bogu GK, Wang M, Rangan ES, Brooks AW, et al., Snyder MP. 2022. Real-time alerting system for COVID-19 and other stress events using wearable data. Nature Medicine 28:175–184.",
      "url": "https://www.nature.com/articles/s41591-021-01593-2",
      "verification": "verified",
      "derivation": "published",
      "evidence_strength": null
    }
  },
  "plan_steps": [
    {
      "id": "st-1",
      "text": "Go to bed an hour earlier for the next 3 nights.",
      "done": false,
      "done_at": null
    },
    {
      "id": "st-2",
      "text": "Take your temperature morning and evening.",
      "done": false,
      "done_at": null
    },
    "… încă 1 elemente de același fel"
  ],
  "recheck_at": "2027-04-16T07:00:00Z",
  "packet_id": null,
  "earth_reply": null,
  "history": [
    {
      "at": "2027-04-13T07:00:00Z",
      "actor": "SHADOW",
      "role": null,
      "action": "created",
      "note": null
    },
    {
      "at": "2027-04-14T07:00:00Z",
      "actor": "SHADOW",
      "role": null,
      "action": "escalated",
      "note": "Escalated automatically to level 2."
    }
  ]
}
```

</details>

---

#### `POST /api/v1/alerts/{alert_id}/ack` — Confirm you have seen the alert

**Cine poate apela:** astronaut, ofițer medical (cmo)

Moves the alert from `active` to `acknowledged`. Not allowed on an alert that is already escalated or
resolved (409 `invalid_state`).

**SSE:** `alert.updated`.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `alert_id` | cale | text | da |  |

**Răspuns 200:** [Alert](#alert)

**Erori posibile:** 401, 403, 404, 422, 409 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
POST /api/v1/alerts/al-0006/ack
```

Răspuns `200`:

```json
{
  "id": "al-0006",
  "crew_id": "cm-2",
  "topic": "behavioral",
  "level": 1,
  "status": "watch",
  "state": "acknowledged",
  "title": "Typing 18% slower than usual",
  "created_at": "2027-04-14T07:17:08.050896Z",
  "explanation": "Your typing rhythm has drifted from your personal baseline (fatigue index 72/100). Typing rhythm can change with fatigue even when you feel rested. Only the timing of key presses is analysed, never what you type.",
  "cause": "individual",
  "cause_explanation": "Only you have this deviation; the rest of the crew is within their usual range.",
  "evidence": [
    {
      "metric_key": "keys_per_min",
      "label": "Typing speed",
      "value": 172.9,
      "unit": "keys/min",
      "baseline": 210.8,
      "deviation_text": "-18% vs your baseline"
    },
    {
      "metric_key": "hold_ms_mean",
      "label": "Key hold time",
      "value": 115.3,
      "unit": "ms",
      "baseline": 95.7,
      "deviation_text": "+21% vs your baseline"
    }
  ],
  "recommendation": {
    "id": "behavioral-1-1",
    "topic": "behavioral",
    "level": 1,
    "trigger": "The PVT-B or typing shows a deviation from your personal baseline (e.g. 1/RT below threshold), even if you feel rested",
    "action": "Don't rely on how you feel: repeat the 3-minute PVT-B before any critical task and, if possible, postpone the task until your results are back to normal.",
    "hrp_risk": "Risk of Performance Decrements and Adverse Health Outcomes Resulting from Sleep Loss, Circadian Desynchronization, and Work Overload",
    "hrp_risk_url": "https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=100",
    "source": {
      "citation": "Van Dongen HPA, Maislin G, Mullington JM, Dinges DF. (2003). The cumulative cost of additional wakefulness: dose-response effects on neurobehavioral functions and sleep physiology from chronic sleep restriction and total sleep deprivation. Sleep 26(2):117-126. Erratum: Sleep 2004;27(4):600. + NASA Evidence Report 2016 (Chronic Sleep Loss section)",
      "url": "https://pubmed.ncbi.nlm.nih.gov/12683469/",
      "verification": "verified",
      "derivation": "published",
      "evidence_strength": null
    }
  },
  "plan_steps": [
    {
      "id": "st-1",
      "text": "Take the 3-minute reaction test.",
      "done": false,
      "done_at": null
    },
    {
      "id": "st-2",
      "text": "Postpone critical tasks by 2 hours, if possible.",
      "done": false,
      "done_at": null
    }
  ],
  "recheck_at": "2027-04-15T07:17:08.050896Z",
  "packet_id": null,
  "earth_reply": null,
  "history": [
    {
      "at": "2027-04-14T07:17:08.050896Z",
      "actor": "SHADOW",
      "role": null,
      "action": "created",
      "note": null
    },
    {
      "at": "2027-04-15T07:02:51.388237Z",
      "actor": "Mission Specialist 2",
      "role": "astronaut",
      "action": "acknowledged",
      "note": null
    }
  ]
}
```

</details>

---

#### `PUT /api/v1/alerts/{alert_id}/plan/steps/{step_id}` — Tick a plan step

**Cine poate apela:** astronaut, ofițer medical (cmo)

Ticks or unticks a step of the action plan.

**SSE:** `alert.updated`.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `alert_id` | cale | text | da |  |
| `step_id` | cale | text | da |  |

**Corpul cererii:** [StepUpdate](#stepupdate)

**Răspuns 200:** [Alert](#alert)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
PUT /api/v1/alerts/al-0005/plan/steps/st-2
```

Cerere:

```json
{
  "done": true
}
```

Răspuns `200`:

```json
{
  "id": "al-0005",
  "crew_id": "cm-2",
  "topic": "immune",
  "level": 2,
  "status": "alert",
  "state": "escalated",
  "title": "Night pulse +7 bpm, 3 nights in a row",
  "created_at": "2027-04-13T07:00:00Z",
  "explanation": "Your night pulse has been at least 4 bpm above your personal median (53.9 bpm) for 3 nights in a row. In the NightSignal study this pattern often came before symptoms of an infection. Tell the crew medical officer.",
  "cause": "individual",
  "cause_explanation": "Only you have this deviation; the rest of the crew is within their usual range.",
  "evidence": [
    {
      "metric_key": "night_pulse_bpm",
      "label": "Night pulse",
      "value": 60.9,
      "unit": "bpm",
      "baseline": 53.9,
      "deviation_text": "+7.0 bpm above your personal median, 3 nights in a row"
    },
    {
      "metric_key": "temperature_c",
      "label": "Temperature",
      "value": 37.3,
      "unit": "°C",
      "baseline": 36.9,
      "deviation_text": "+0.4 °C vs your in-flight median"
    },
    "… încă 1 elemente de același fel"
  ],
  "recommendation": {
    "id": "immune-2-1",
    "topic": "immune",
    "level": 2,
    "trigger": "NightSignal red alert: mean night-time heart rate ≥ +4 bpm above your personal median two nights in a row, especially if skin temperature exceeds the derived SHADOW threshold or symptoms appear.",
    "action": "Notify the crew medical officer (CMO) with the heart rate and temperature chart against your baseline and your symptom journal. Only the CMO decides on assessment or treatment; the app does not recommend medicines.",
    "hrp_risk": "Risk of In Mission Impacts, Adverse Health Events or Long-Term Health Impacts due to Altered Immune Response",
    "hrp_risk_url": "https://humanresearchroadmap.nasa.gov/Risks/?i=85",
    "source": {
      "citation": "Alavi A, Bogu GK, Wang M, Rangan ES, Brooks AW, et al., Snyder MP. 2022. Real-time alerting system for COVID-19 and other stress events using wearable data. Nature Medicine 28:175–184.",
      "url": "https://www.nature.com/articles/s41591-021-01593-2",
      "verification": "verified",
      "derivation": "published",
      "evidence_strength": null
    }
  },
  "plan_steps": [
    {
      "id": "st-1",
      "text": "Go to bed an hour earlier for the next 3 nights.",
      "done": false,
      "done_at": null
    },
    {
      "id": "st-2",
      "text": "Take your temperature morning and evening.",
      "done": true,
      "done_at": "2027-04-15T07:02:51.910227Z"
    },
    "… încă 1 elemente de același fel"
  ],
  "recheck_at": "2027-04-16T07:00:00Z",
  "packet_id": null,
  "earth_reply": null,
  "history": [
    {
      "at": "2027-04-13T07:00:00Z",
      "actor": "SHADOW",
      "role": null,
      "action": "created",
      "note": null
    },
    {
      "at": "2027-04-14T07:00:00Z",
      "actor": "SHADOW",
      "role": null,
      "action": "escalated",
      "note": "Escalated automatically to level 2."
    },
    "… încă 1 elemente de același fel"
  ]
}
```

</details>

---

#### `POST /api/v1/alerts/{alert_id}/escalate` — Escalate the alert

**Cine poate apela:** astronaut, ofițer medical (cmo)

Raises the alert by one level.

* `to_level = 2` — the astronaut sends it to the crew medical officer. It shows up in `/cmo/queue`.
* `to_level = 3` — **only the `cmo` role**. The backend automatically creates a signed and encrypted packet in
  the queue to Earth and puts its id in `packet_id`. There is no need to call `/link/outbox`.

The level can never go down (409 `invalid_state`). Critical alerts can also be escalated automatically by the
triage engine.

**SSE:** `alert.updated`, and at level 3 also `packet.sent` when the window opens.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `alert_id` | cale | text | da |  |

**Corpul cererii:** [EscalateRequest](#escalaterequest)

**Răspuns 200:** [Alert](#alert)

**Erori posibile:** 401, 403, 404, 422, 409 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>medic</code>)</summary>

```http
POST /api/v1/alerts/al-0005/escalate
```

Cerere:

```json
{
  "to_level": 3,
  "note": "A treia noapte la rând, temperatură în creștere."
}
```

Răspuns `200`:

```json
{
  "id": "al-0005",
  "crew_id": "cm-2",
  "topic": "immune",
  "level": 3,
  "status": "alert",
  "state": "escalated",
  "title": "Night pulse +7 bpm, 3 nights in a row",
  "created_at": "2027-04-13T07:00:00Z",
  "explanation": "Your night pulse has been at least 4 bpm above your personal median (53.9 bpm) for 3 nights in a row. In the NightSignal study this pattern often came before symptoms of an infection. Tell the crew medical officer.",
  "cause": "individual",
  "cause_explanation": "Only you have this deviation; the rest of the crew is within their usual range.",
  "evidence": [
    {
      "metric_key": "night_pulse_bpm",
      "label": "Night pulse",
      "value": 60.9,
      "unit": "bpm",
      "baseline": 53.9,
      "deviation_text": "+7.0 bpm above your personal median, 3 nights in a row"
    },
    {
      "metric_key": "temperature_c",
      "label": "Temperature",
      "value": 37.3,
      "unit": "°C",
      "baseline": 36.9,
      "deviation_text": "+0.4 °C vs your in-flight median"
    },
    "… încă 1 elemente de același fel"
  ],
  "recommendation": {
    "id": "immune-2-1",
    "topic": "immune",
    "level": 2,
    "trigger": "NightSignal red alert: mean night-time heart rate ≥ +4 bpm above your personal median two nights in a row, especially if skin temperature exceeds the derived SHADOW threshold or symptoms appear.",
    "action": "Notify the crew medical officer (CMO) with the heart rate and temperature chart against your baseline and your symptom journal. Only the CMO decides on assessment or treatment; the app does not recommend medicines.",
    "hrp_risk": "Risk of In Mission Impacts, Adverse Health Events or Long-Term Health Impacts due to Altered Immune Response",
    "hrp_risk_url": "https://humanresearchroadmap.nasa.gov/Risks/?i=85",
    "source": {
      "citation": "Alavi A, Bogu GK, Wang M, Rangan ES, Brooks AW, et al., Snyder MP. 2022. Real-time alerting system for COVID-19 and other stress events using wearable data. Nature Medicine 28:175–184.",
      "url": "https://www.nature.com/articles/s41591-021-01593-2",
      "verification": "verified",
      "derivation": "published",
      "evidence_strength": null
    }
  },
  "plan_steps": [
    {
      "id": "st-1",
      "text": "Go to bed an hour earlier for the next 3 nights.",
      "done": false,
      "done_at": null
    },
    {
      "id": "st-2",
      "text": "Take your temperature morning and evening.",
      "done": true,
      "done_at": "2027-04-15T07:02:51.910227Z"
    },
    "… încă 1 elemente de același fel"
  ],
  "recheck_at": "2027-04-16T07:00:00Z",
  "packet_id": "pk-0001",
  "earth_reply": null,
  "history": [
    {
      "at": "2027-04-13T07:00:00Z",
      "actor": "SHADOW",
      "role": null,
      "action": "created",
      "note": null
    },
    {
      "at": "2027-04-14T07:00:00Z",
      "actor": "SHADOW",
      "role": null,
      "action": "escalated",
      "note": "Escalated automatically to level 2."
    },
    "… încă 3 elemente de același fel"
  ]
}
```

</details>

---

#### `POST /api/v1/alerts/{alert_id}/resolve` — Close the alert

**Cine poate apela:** astronaut, ofițer medical (cmo)

An astronaut can close level 1 alerts; level 2 and 3 alerts are closed by the crew medical officer.
`outcome = monitoring` keeps the alert open and moves `recheck_at` by one more day.

**SSE:** `alert.updated`.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `alert_id` | cale | text | da |  |

**Corpul cererii:** [ResolveRequest](#resolverequest)

**Răspuns 200:** [Alert](#alert)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
POST /api/v1/alerts/al-0006/resolve
```

Cerere:

```json
{
  "outcome": "resolved",
  "note": "Testul de reacție a revenit la normal."
}
```

Răspuns `200`:

```json
{
  "id": "al-0006",
  "crew_id": "cm-2",
  "topic": "behavioral",
  "level": 1,
  "status": "watch",
  "state": "resolved",
  "title": "Typing 18% slower than usual",
  "created_at": "2027-04-14T07:17:08.050896Z",
  "explanation": "Your typing rhythm has drifted from your personal baseline (fatigue index 72/100). Typing rhythm can change with fatigue even when you feel rested. Only the timing of key presses is analysed, never what you type.",
  "cause": "individual",
  "cause_explanation": "Only you have this deviation; the rest of the crew is within their usual range.",
  "evidence": [
    {
      "metric_key": "keys_per_min",
      "label": "Typing speed",
      "value": 172.9,
      "unit": "keys/min",
      "baseline": 210.8,
      "deviation_text": "-18% vs your baseline"
    },
    {
      "metric_key": "hold_ms_mean",
      "label": "Key hold time",
      "value": 115.3,
      "unit": "ms",
      "baseline": 95.7,
      "deviation_text": "+21% vs your baseline"
    }
  ],
  "recommendation": {
    "id": "behavioral-1-1",
    "topic": "behavioral",
    "level": 1,
    "trigger": "The PVT-B or typing shows a deviation from your personal baseline (e.g. 1/RT below threshold), even if you feel rested",
    "action": "Don't rely on how you feel: repeat the 3-minute PVT-B before any critical task and, if possible, postpone the task until your results are back to normal.",
    "hrp_risk": "Risk of Performance Decrements and Adverse Health Outcomes Resulting from Sleep Loss, Circadian Desynchronization, and Work Overload",
    "hrp_risk_url": "https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=100",
    "source": {
      "citation": "Van Dongen HPA, Maislin G, Mullington JM, Dinges DF. (2003). The cumulative cost of additional wakefulness: dose-response effects on neurobehavioral functions and sleep physiology from chronic sleep restriction and total sleep deprivation. Sleep 26(2):117-126. Erratum: Sleep 2004;27(4):600. + NASA Evidence Report 2016 (Chronic Sleep Loss section)",
      "url": "https://pubmed.ncbi.nlm.nih.gov/12683469/",
      "verification": "verified",
      "derivation": "published",
      "evidence_strength": null
    }
  },
  "plan_steps": [
    {
      "id": "st-1",
      "text": "Take the 3-minute reaction test.",
      "done": false,
      "done_at": null
    },
    {
      "id": "st-2",
      "text": "Postpone critical tasks by 2 hours, if possible.",
      "done": false,
      "done_at": null
    }
  ],
  "recheck_at": "2027-04-15T07:17:08.050896Z",
  "packet_id": null,
  "earth_reply": null,
  "history": [
    {
      "at": "2027-04-14T07:17:08.050896Z",
      "actor": "SHADOW",
      "role": null,
      "action": "created",
      "note": null
    },
    {
      "at": "2027-04-15T07:02:51.388237Z",
      "actor": "Mission Specialist 2",
      "role": "astronaut",
      "action": "acknowledged",
      "note": null
    },
    "… încă 1 elemente de același fel"
  ]
}
```

</details>

---

#### `GET /api/v1/catalog/recommendations` — Recommendation catalog

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Recommendations written by the team based on the NASA HRP risks, each with its source. The AI doctor only
rephrases them.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `topic` | query | [AlertTopic](#alerttopic) \| null | nu |  |
| `level` | query | număr întreg \| null | nu |  (min 1; max 3) |

**Răspuns 200:** listă de [Recommendation](#recommendation)

**Erori posibile:** 401, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/catalog/recommendations?topic=immune
```

Răspuns `200`:

```json
[
  {
    "id": "immune-1-1",
    "topic": "immune",
    "level": 1,
    "trigger": "Yellow alert: your mean night-time heart rate is +3 bpm above your personal median, or a single night is ≥ +4 bpm (a NightSignal threshold; using it as level 1 is a SHADOW choice).",
    "action": "Fill in the short context journal in the app: symptoms (cough, fever, headache, tiredness), short sleep, stress, hard exercise. Measure again the next night. In the study, alerts were also triggered by stress or other events unrelated to infection, and participants annotated their alerts through questionnaires.",
    "hrp_risk": "Risk of In Mission Impacts, Adverse Health Events or Long-Term Health Impacts due to Altered Immune Response",
    "hrp_risk_url": "https://humanresearchroadmap.nasa.gov/Risks/?i=85",
    "source": {
      "citation": "Alavi A, Bogu GK, Wang M, Rangan ES, Brooks AW, et al., Snyder MP. 2022. Real-time alerting system for COVID-19 and other stress events using wearable data. Nature Medicine 28:175–184.",
      "url": "https://www.nature.com/articles/s41591-021-01593-2",
      "verification": "verified",
      "derivation": "derived",
      "evidence_strength": null
    }
  },
  {
    "id": "immune-1-2",
    "topic": "immune",
    "level": 1,
    "trigger": "Any active immune alert, or sleep below your personal baseline.",
    "action": "Prioritise sleep and fatigue management according to the schedule (sleep and circadian rhythm are directly linked to immune function; in orbit, sleep is shorter and rhythms are misaligned). Use the behavioural and fatigue support services available.",
    "hrp_risk": "Risk of In Mission Impacts, Adverse Health Events or Long-Term Health Impacts due to Altered Immune Response",
    "hrp_risk_url": "https://humanresearchroadmap.nasa.gov/Risks/?i=85",
    "source": {
      "citation": "Crucian BE, Choukèr A, Simpson RJ, Mehta S, Marshall G, Smith SM, et al., Sams C. 2018. Immune System Dysregulation During Spaceflight: Potential Countermeasures for Deep Space Exploration Missions. Frontiers in Immunology 9:1437.",
      "url": "https://www.frontiersin.org/articles/10.3389/fimmu.2018.01437/full",
      "verification": "verified",
      "derivation": "published",
      "evidence_strength": null
    }
  },
  "… încă 8 elemente de același fel"
]
```

</details>

---

#### `GET /api/v1/catalog/recommendations/{rec_id}` — One catalog recommendation

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `rec_id` | cale | text | da |  |

**Răspuns 200:** [Recommendation](#recommendation)

**Erori posibile:** 401, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/catalog/recommendations/immune-2-1
```

Răspuns `200`:

```json
{
  "id": "immune-2-1",
  "topic": "immune",
  "level": 2,
  "trigger": "NightSignal red alert: mean night-time heart rate ≥ +4 bpm above your personal median two nights in a row, especially if skin temperature exceeds the derived SHADOW threshold or symptoms appear.",
  "action": "Notify the crew medical officer (CMO) with the heart rate and temperature chart against your baseline and your symptom journal. Only the CMO decides on assessment or treatment; the app does not recommend medicines.",
  "hrp_risk": "Risk of In Mission Impacts, Adverse Health Events or Long-Term Health Impacts due to Altered Immune Response",
  "hrp_risk_url": "https://humanresearchroadmap.nasa.gov/Risks/?i=85",
  "source": {
    "citation": "Alavi A, Bogu GK, Wang M, Rangan ES, Brooks AW, et al., Snyder MP. 2022. Real-time alerting system for COVID-19 and other stress events using wearable data. Nature Medicine 28:175–184.",
    "url": "https://www.nature.com/articles/s41591-021-01593-2",
    "verification": "verified",
    "derivation": "published",
    "evidence_strength": null
  }
}
```

</details>

---

### 8. Link with Earth

#### `GET /api/v1/link/status` — Link status

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

The current delay, whether the window is open and how many packets wait in each direction.

**Răspuns 200:** [LinkStatus](#linkstatus)

**Erori posibile:** 401, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>earth</code>)</summary>

```http
GET /api/v1/link/status
```

Răspuns `200`:

```json
{
  "environment": "mars_transit",
  "one_way_delay_s": 700.0,
  "one_way_delay_real_s": 11.67,
  "window_open": true,
  "window_closes_at": null,
  "next_window_at": null,
  "queued_down": 1,
  "queued_up": 0
}
```

</details>

---

#### `GET /api/v1/link/packets` — Packet queue

**Cine poate apela:** ofițer medical (cmo), Pământ (earth)

The packet envelopes, newest first — the table on the "Mission Control" screen.

The `progress` field is computed at response time. For a smooth bar, animate locally using `eta_real_s` and
reload the list only on SSE `packet.sent` / `packet.arrived` / `packet.rejected`.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `direction` | query | [PacketDirection](#packetdirection) \| null | nu |  |
| `status` | query | [PacketStatus](#packetstatus) \| null | nu |  |
| `limit` | query | număr întreg | nu |  Implicit: `50`. (min 1; max 200) |

**Răspuns 200:** listă de [Packet](#packet)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>earth</code>)</summary>

```http
GET /api/v1/link/packets?direction=down
```

Răspuns `200`:

```json
[
  {
    "id": "pk-0001",
    "seq": 1,
    "direction": "down",
    "kind": "alert_l3",
    "status": "queued",
    "title": "Sentinel · Night pulse +7 bpm, 3 nights in a row",
    "sender": "Crew Medical Officer",
    "level": 3,
    "alert_status": "alert",
    "crew_id": "cm-2",
    "alert_id": "al-0005",
    "in_reply_to": null,
    "created_at": "2027-04-15T07:02:53.061874Z",
    "sent_at": null,
    "arrives_at": null,
    "delivered_at": null,
    "progress": 0.0,
    "eta_real_s": null,
    "signature_valid": null,
    "reject_reason": null,
    "size_bytes": 4285
  }
]
```

</details>

---

#### `GET /api/v1/link/packets/{packet_id}` — One packet, with the decrypted content

**Cine poate apela:** ofițer medical (cmo), Pământ (earth)

`payload` appears only for `delivered` packets. The `earth` role sees the content of `down` packets that
arrived; the `cmo` role sees the content of `up` packets that arrived and of the ones they sent. Otherwise
`payload` is `null`.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `packet_id` | cale | text | da |  |

**Răspuns 200:** [PacketDetail](#packetdetail)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>earth</code>)</summary>

```http
GET /api/v1/link/packets/pk-0001
```

Răspuns `200`:

```json
{
  "id": "pk-0001",
  "seq": 1,
  "direction": "down",
  "kind": "alert_l3",
  "status": "queued",
  "title": "Sentinel · Night pulse +7 bpm, 3 nights in a row",
  "sender": "Crew Medical Officer",
  "level": 3,
  "alert_status": "alert",
  "crew_id": "cm-2",
  "alert_id": "al-0005",
  "in_reply_to": null,
  "created_at": "2027-04-15T07:02:53.061874Z",
  "sent_at": null,
  "arrives_at": null,
  "delivered_at": null,
  "progress": 0.0,
  "eta_real_s": null,
  "signature_valid": null,
  "reject_reason": null,
  "size_bytes": 4285,
  "payload": null,
  "crypto": {
    "cipher": "AES-256-GCM",
    "signature_alg": "Ed25519",
    "key_id": "ship-2026-01",
    "nonce_b64": "mTTyu16Ufc5jDI+g",
    "signature_b64": "QBbIdruw8HoFRfBq6lM/roYLqtmvnjV1xEJx84BiiyrmXXxeW1Kemsx/k874o6KF/Wpb4ZdopMuJbcPz78CdAw=="
  }
}
```

</details>

---

#### `POST /api/v1/link/outbox` — Put a message in the queue to Earth

**Cine poate apela:** astronaut, ofițer medical (cmo)

For the weekly summary approved by the astronaut (`weekly_summary`). An astronaut can send only about
their own `crew_id`.

Level 3 alerts enter the queue automatically, through `/alerts/{id}/escalate`. `alert_l3` here only sends one
**again**: crew medical officer only (`403` otherwise), and only for an alert already at level 3 (`409`
otherwise).

The packet starts `queued` and leaves at the next communication window.

**SSE:** `packet.sent` when it leaves, `packet.arrived` when it arrives.

**Corpul cererii:** [OutboxCreate](#outboxcreate)

**Răspuns 201:** [Packet](#packet)

**Erori posibile:** 401, 403, 404, 422, 409 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
POST /api/v1/link/outbox
```

Cerere:

```json
{
  "kind": "weekly_summary",
  "crew_id": "cm-2",
  "body": "Săptămâna 14: aprob trimiterea rezumatului."
}
```

Răspuns `201`:

```json
{
  "id": "pk-0002",
  "seq": 2,
  "direction": "down",
  "kind": "weekly_summary",
  "status": "queued",
  "title": "Weekly summary · week 14",
  "sender": "Mission Specialist 2",
  "level": null,
  "alert_status": null,
  "crew_id": "cm-2",
  "alert_id": null,
  "in_reply_to": null,
  "created_at": "2027-04-15T07:02:56.336367Z",
  "sent_at": null,
  "arrives_at": null,
  "delivered_at": null,
  "progress": 0.0,
  "eta_real_s": null,
  "signature_valid": null,
  "reject_reason": null,
  "size_bytes": 305
}
```

</details>

---

#### `POST /api/v1/earth/replies` — The reply of the flight surgeon on Earth

**Cine poate apela:** Pământ (earth)

The "Queue, encrypted" button on Mission Control. The reply leaves at the next window and reaches the ship
after `one_way_delay_s`. When it arrives, it shows up in `/crew/{id}/messages` and in the alert's `earth_reply`.

**SSE:** `packet.sent`, then `packet.arrived` (with `crew_id`) on arrival.

**Corpul cererii:** [EarthReplyCreate](#earthreplycreate)

**Răspuns 201:** [Packet](#packet)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>earth</code>)</summary>

```http
POST /api/v1/earth/replies
```

Cerere:

```json
{
  "in_reply_to": "pk-0002",
  "crew_id": "cm-2",
  "alert_id": "al-0005",
  "body": "De acord cu odihna. Temperatura de două ori pe zi; dacă depășește 38 °C, anunțați-ne."
}
```

Răspuns `201`:

```json
{
  "id": "pk-0003",
  "seq": 1,
  "direction": "up",
  "kind": "earth_reply",
  "status": "queued",
  "title": "Reply: De acord cu odihna. Temperatura de două ori pe zi; dacă depă",
  "sender": "Flight Surgeon",
  "level": null,
  "alert_status": null,
  "crew_id": "cm-2",
  "alert_id": "al-0005",
  "in_reply_to": "pk-0002",
  "created_at": "2027-04-15T07:02:57.235711Z",
  "sent_at": null,
  "arrives_at": null,
  "delivered_at": null,
  "progress": 0.0,
  "eta_real_s": null,
  "signature_valid": null,
  "reject_reason": null,
  "size_bytes": 353
}
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/messages` — Messages arrived from Earth

**Cine poate apela:** astronaut, ofițer medical (cmo)

The flight surgeon's replies and the DONKI warnings that HAVE ARRIVED on board, already decrypted and
verified. The ones still on their way do not appear here.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |

**Răspuns 200:** listă de [CrewMessage](#crewmessage)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/crew/cm-2/messages
```

Răspuns `200`:

```json
[]
```

</details>

---

### 9. Radiation and the solar storm

#### `GET /api/v1/radiation/status` — Radiation now

**Cine poate apela:** astronaut, ofițer medical (cmo)

The dose rate at the on-board dosimeter, the 24-h mean, whether there is an alert and whether the crew is in
the shelter.

`lead_minutes` is filled in when the DONKI warning from Earth arrives: the number of minutes SHADOW was faster.
Show it big; it is the number in the pitch.

The `earth` role has NO access: Earth does not see the ship's dosimeter in real time, only what comes through
the queue.

**Răspuns 200:** [RadiationStatus](#radiationstatus)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/radiation/status
```

Răspuns `200`:

```json
{
  "at": "2027-04-15T07:02:58.017056Z",
  "dose_rate_usv_h": 64.99,
  "mean_24h_usv_h": 65.82,
  "ratio": 0.99,
  "threshold_ratio": 2.0,
  "alert_active": false,
  "alert_id": null,
  "sheltered": false,
  "sheltered_since": null,
  "event": null,
  "event_dose_msv": 0.0,
  "onboard_alert_at": null,
  "earth_warning_arrived_at": null,
  "lead_minutes": null,
  "profile_is_synthetic": true
}
```

</details>

---

#### `GET /api/v1/radiation/series` — The dose curve (chart)

**Cine poate apela:** astronaut, ofițer medical (cmo)

The points of the dose chart. Reload on SSE `radiation.reading` (at most once every 2 real seconds).

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `hours` | query | număr | nu | How many mission hours back. Implicit: `24`. (max 240; > 0) |
| `step_min` | query | număr întreg | nu |  Implicit: `10`. (min 1; max 120) |

**Răspuns 200:** [RadiationSeries](#radiationseries)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/radiation/series?hours=1&step_min=10
```

Răspuns `200`:

```json
{
  "unit": "µSv/h",
  "threshold_ratio": 2.0,
  "points": [
    {
      "t": "2027-04-15T06:12:14.051972Z",
      "dose_rate_usv_h": 67.4,
      "mean_24h_usv_h": 65.9,
      "sheltered": false
    },
    {
      "t": "2027-04-15T06:22:14.051972Z",
      "dose_rate_usv_h": 63.24,
      "mean_24h_usv_h": 65.86,
      "sheltered": false
    },
    "… încă 3 elemente de același fel"
  ]
}
```

</details>

---

#### `GET /api/v1/radiation/events` — The available DONKI events

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

The real NASA DONKI events loaded from the file (offline). For now one: 11 May 2024.

**Răspuns 200:** listă de [SepEvent](#sepevent)

**Erori posibile:** 401, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/radiation/events
```

Răspuns `200`:

```json
[
  {
    "donki_id": "2024-05-11T02:10:00-SEP-001",
    "event_time": "2024-05-11T02:10:00Z",
    "sim_onset_at": null,
    "instrument": "GOES-P: SEISS >100 MeV",
    "flare_class": "X5.8",
    "cme_id": "2024-05-11T01:36:00-CME-001",
    "donki_url": "https://ccmc.gsfc.nasa.gov/DONKI/view/SEP/30714/-1",
    "note": "GLE 74, Gannon storm (May 2024). The dose curve is synthetic; the event time is real."
  }
]
```

</details>

---

#### `POST /api/v1/radiation/shelter-ack` — "I am in the shelter"

**Cine poate apela:** astronaut, ofițer medical (cmo)

The astronaut confirms they reached the shelter (or left it). From then on the simulator applies the
shielding factor, and the time is saved.

**SSE:** `radiation.reading`.

**Corpul cererii:** [ShelterAck](#shelterack)

**Răspuns 200:** [RadiationStatus](#radiationstatus)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
POST /api/v1/radiation/shelter-ack
```

Cerere:

```json
{
  "sheltered": true
}
```

Răspuns `200`:

```json
{
  "at": "2027-04-15T07:02:59.642622Z",
  "dose_rate_usv_h": 20.65,
  "mean_24h_usv_h": 65.82,
  "ratio": 0.31,
  "threshold_ratio": 2.0,
  "alert_active": false,
  "alert_id": null,
  "sheltered": true,
  "sheltered_since": "2027-04-15T07:02:59.197479Z",
  "event": null,
  "event_dose_msv": 0.0,
  "onboard_alert_at": null,
  "earth_warning_arrived_at": null,
  "lead_minutes": null,
  "profile_is_synthetic": true
}
```

</details>

---

### 10. AI doctor

#### `GET /api/v1/ai/status` — Model status

**Cine poate apela:** astronaut, ofițer medical (cmo)

Whether the local model is loaded. When `ready` is `false`, the AI card shows only the catalog text.

**Răspuns 200:** [AiStatus](#aistatus)

**Erori posibile:** 401, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/ai/status
```

Răspuns `200`:

```json
{
  "ready": false,
  "model": null,
  "mode": "fallback"
}
```

</details>

---

#### `POST /api/v1/ai/chat` — Ask the AI doctor

**Cine poate apela:** astronaut, ofițer medical (cmo)

A short answer, with NASA sources (RAG), that rephrases the catalog recommendation. **The AI does not decide
the triage.**

* It can take 5–15 seconds on a laptop: show a loading state.
* If the model does not answer within 20 seconds or is off, the endpoint does NOT fail: it returns the catalog
  text, with `fallback = true`. The app works without AI.
* An astronaut can ask only about their own `crew_id`.

**Corpul cererii:** [AiChatRequest](#aichatrequest)

**Răspuns 200:** [AiChatResponse](#aichatresponse)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
POST /api/v1/ai/chat
```

Cerere:

```json
{
  "crew_id": "cm-2",
  "message": "De ce mi-a crescut pulsul de noapte?",
  "alert_id": "al-0005",
  "history": []
}
```

Răspuns `200`:

```json
{
  "answer": "Notify the crew medical officer (CMO) with the heart rate and temperature chart against your baseline and your symptom journal. Only the CMO decides on assessment or treatment; the app does not recommend medicines.",
  "citations": [
    {
      "title": "Alavi A, Bogu GK, Wang M, Rangan ES, Brooks AW, et al., Snyder MP. 2022. Real-time alerting system for COVID-19 and other stress events using wearable data. Nature Medicine 28:175–184.",
      "url": "https://www.nature.com/articles/s41591-021-01593-2",
      "snippet": "NightSignal red alert: mean night-time heart rate ≥ +4 bpm above your personal median two nights in a row, especially if skin temperature exceeds the derived SHADOW threshold or symptoms appear."
    }
  ],
  "recommendation_ids": [
    "immune-2-1"
  ],
  "model": "catalog",
  "latency_ms": 40,
  "fallback": true,
  "disclaimer": "Decision-support prototype, not a medical device."
}
```

</details>

---

### 11. Security and evidence

#### `GET /api/v1/access-log` — Access log

**Cine poate apela:** astronaut, ofițer medical (cmo)

Who read what, newest first. An astronaut sees who accessed their data; the crew medical officer sees the
whole log. The log is append-only: every entry holds the hash of the previous one (`prev_hash`), so it cannot be
changed silently.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | query | text \| null | nu | Astronaut: ignored, they always see only access to their own data. |
| `limit` | query | număr întreg | nu |  Implicit: `50`. (min 1; max 500) |

**Răspuns 200:** listă de [AccessLogEntry](#accesslogentry)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/access-log
```

Răspuns `200`:

```json
[
  {
    "id": 3,
    "at": "2027-04-15T07:02:53.413761Z",
    "actor": "Crew Medical Officer",
    "actor_role": "cmo",
    "action": "escalate",
    "resource": "alerts/al-0005",
    "crew_id": "cm-2",
    "outcome": "allowed",
    "prev_hash": "a4994e8967f1e109",
    "hash": "378ad42b75257809"
  },
  {
    "id": 2,
    "at": "2027-04-15T07:02:28.126592Z",
    "actor": "Mission Specialist 2",
    "actor_role": "astronaut",
    "action": "logout",
    "resource": "auth/logout",
    "crew_id": "cm-2",
    "outcome": "allowed",
    "prev_hash": "529164d23f9d10b5",
    "hash": "a4994e8967f1e109"
  },
  "… încă 1 elemente de același fel"
]
```

</details>

---

#### `GET /api/v1/access-log/integrity` — Is the access log intact

**Cine poate apela:** astronaut, ofițer medical (cmo)

Recomputes the hash chain of the **whole** log, from the first entry to the last, and says whether it still
holds. `intact = false` means an entry was changed or removed directly in the database.

What the chain cannot show: the newest entries removed from the end. That needs the last hash kept somewhere
outside the log.

Frontend: show the result above the access log; on `false`, show it as an alert.

**Răspuns 200:** [AccessLogIntegrity](#accesslogintegrity)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/access-log/integrity
```

Răspuns `200`:

```json
{
  "intact": true,
  "entries": 3,
  "checked_at": "2027-04-15T07:03:08.941460Z"
}
```

</details>

---

#### `GET /api/v1/security/rejections` — Rejected data and packets

**Cine poate apela:** astronaut, ofițer medical (cmo)

Impossible values, "frozen" sensors, invalid signatures and replayed packets, newest first.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `limit` | query | număr întreg | nu |  Implicit: `50`. (min 1; max 500) |

**Răspuns 200:** listă de [Rejection](#rejection)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>medic</code>)</summary>

```http
GET /api/v1/security/rejections
```

Răspuns `200`:

```json
[]
```

</details>

---

#### `POST /api/v1/ingest/measurements` — Receive a measurement from a device

**Cine poate apela:** dispozitiv (semnătură Ed25519, fără JWT)

**Not for the frontend.** Called by the simulator and the devices. It does not use a JWT: authentication is
the device's Ed25519 signature, checked with the public key registered for `device_id`.

Checks, in order: signature → plausibility of the value → frozen sensor (the same value too many times).
A rejected measurement still returns 200, with `accepted = false`, and shows up in `/security/rejections`.

**SSE:** `measurement.rejected` on rejection.

**Corpul cererii:** [MeasurementIngest](#measurementingest)

**Răspuns 200:** [IngestResult](#ingestresult)

**Erori posibile:** 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>nimeni</code>)</summary>

```http
POST /api/v1/ingest/measurements
```

Cerere:

```json
{
  "device_id": "wearable-cm-2",
  "crew_id": "cm-2",
  "metric_key": "night_pulse_bpm",
  "value": 61,
  "unit": "bpm",
  "measured_at": "2027-04-15T03:00:00Z",
  "signature_b64": "MEUCIQDc...trunchiat..."
}
```

Răspuns `200`:

```json
{
  "accepted": false,
  "rejection": {
    "id": "rj-0001",
    "at": "2027-04-15T07:03:09.508535Z",
    "kind": "bad_signature",
    "source": "wearable-cm-2",
    "crew_id": "cm-2",
    "metric_key": "night_pulse_bpm",
    "value": 61.0,
    "message": "Invalid signature from wearable-cm-2: the measurement was discarded."
  }
}
```

</details>

---

#### `GET /api/v1/evidence/tests` — Automated test results

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

The latest pytest report on the protocol engine, for the Evidence screen (run once at server start).

**Răspuns 200:** [TestReport](#testreport)

**Erori posibile:** 401, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/evidence/tests
```

Răspuns `200`:

```json
{
  "ran_at": "2027-04-15T07:03:09.836357Z",
  "passed": 0,
  "failed": 0,
  "skipped": 0,
  "duration_s": 0.0,
  "tests": []
}
```

</details>

---

#### `GET /api/v1/evidence/parameters` — Thresholds and their sources

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

The content of `parameters.json`: every threshold with value, unit, explanation and source, marked
verified/unverified and published/derived.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `topic` | query | text \| null | nu | comportamental / cardiovascular / imunitar / oase_muschi / radiatii / comunicare |
| `key_only` | query | true/false | nu | Only the thresholds used directly by the triage engine. Implicit: `False`. |

**Răspuns 200:** listă de [Parameter](#parameter)

**Erori posibile:** 401, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/evidence/parameters?key_only=true
```

Răspuns `200`:

```json
[
  {
    "id": "acien_sessions_for_detection",
    "topic": "comportamental",
    "name": "Consecutive sessions needed for continuous detection",
    "value": 4,
    "unit": "typing sessions",
    "explanation": "In continuous detection mode (quick change detection), the model detects fatigue after 4 sessions with AUC 80% (EER 20%). This suggests an alert should require a sustained deviation over several sessions, not a single one.",
    "is_key_threshold": true,
    "source": {
      "citation": "Acien A, Morales A, Vera-Rodriguez R, Fierrez J, Mondesire-Crump I, Arroyo-Gallego T. (2022). Detection of Mental Fatigue in the General Population: Feasibility Study of Keystroke Dynamics as a Real-world Biomarker. JMIR Biomedical Engineering 7(2):e41003 (published 21 Nov 2022).",
      "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11041424/",
      "verification": "verified",
      "derivation": "published",
      "evidence_strength": "weak"
    }
  },
  {
    "id": "keystroke_baseline_duration",
    "topic": "comportamental",
    "name": "Minimum length of the typing baseline",
    "value": 7,
    "unit": "days",
    "explanation": "None of the sources read sets a minimum number of days or sessions for a stable typing baseline. Working proposal: ≥7 days covering every time of day (speed has a daily rhythm), normalised by time slot.",
    "is_key_threshold": true,
    "source": {
      "citation": "Fang Y, Yang P, Frank E, Goldstein C, Wright AGC, Bohnert ASB, et al. (2026). Patterns of smartphone typing performance by time awake: implications for unobtrusive ambulatory mental fatigue assessment. PLOS Digital Health 5(3):e0001281.",
      "url": "https://journals.plos.org/digitalhealth/article?id=10.1371/journal.pdig.0001281",
      "verification": "unverified",
      "derivation": "derived",
      "evidence_strength": "weak"
    }
  },
  "… încă 31 elemente de același fel"
]
```

</details>

---

### 12. Demo and simulator

#### `POST /api/v1/sim/sep/start` — Start the solar storm

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

The demo button. The simulator replays the real event from DONKI:

1. the dose rate at the dosimeter rises → after 3 readings above 2× the mean, SHADOW gives the level 1 alert
   (`radiation.alert`);
2. Earth's warning leaves the queue as a `donki_alert` packet, direction `up`, at the time of NASA's alert
   (20 minutes after the onset), and arrives after the link delay;
3. on arrival, `lead_minutes` is filled in in `/radiation/status`.

**SSE:** `radiation.alert`, `alert.created`, `radiation.reading`, `packet.sent`, then `packet.arrived`.

**Corpul cererii:** [SepStart](#sepstart)

**Răspuns 200:** [RadiationStatus](#radiationstatus)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>medic</code>)</summary>

```http
POST /api/v1/sim/sep/start
```

Cerere:

```json
{
  "event_id": "2024-05-11T02:10:00-SEP-001",
  "starts_in_min": 0
}
```

Răspuns `200`:

```json
{
  "at": "2027-04-15T07:03:10.494971Z",
  "dose_rate_usv_h": 21.91,
  "mean_24h_usv_h": 65.82,
  "ratio": 0.33,
  "threshold_ratio": 2.0,
  "alert_active": false,
  "alert_id": null,
  "sheltered": true,
  "sheltered_since": "2027-04-15T07:02:59.197479Z",
  "event": {
    "donki_id": "2024-05-11T02:10:00-SEP-001",
    "event_time": "2024-05-11T02:10:00Z",
    "sim_onset_at": "2027-04-15T07:03:10.354932Z",
    "instrument": "GOES-P: SEISS >100 MeV",
    "flare_class": "X5.8",
    "cme_id": "2024-05-11T01:36:00-CME-001",
    "donki_url": "https://ccmc.gsfc.nasa.gov/DONKI/view/SEP/30714/-1",
    "note": "GLE 74, Gannon storm (May 2024). The dose curve is synthetic; the event time is real."
  },
  "event_dose_msv": 0.0,
  "onboard_alert_at": null,
  "earth_warning_arrived_at": null,
  "lead_minutes": null,
  "profile_is_synthetic": true
}
```

</details>

---

#### `POST /api/v1/sim/sep/stop` — Stop the solar storm

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Brings the dose rate back to the background. **SSE:** `radiation.cleared`.

**Răspuns 200:** [RadiationStatus](#radiationstatus)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>medic</code>)</summary>

```http
POST /api/v1/sim/sep/stop
```

Răspuns `200`:

```json
{
  "at": "2027-04-15T07:03:11.098315Z",
  "dose_rate_usv_h": 21.9,
  "mean_24h_usv_h": 65.82,
  "ratio": 0.33,
  "threshold_ratio": 2.0,
  "alert_active": false,
  "alert_id": null,
  "sheltered": true,
  "sheltered_since": "2027-04-15T07:02:59.197479Z",
  "event": null,
  "event_dose_msv": 0.0,
  "onboard_alert_at": null,
  "earth_warning_arrived_at": null,
  "lead_minutes": null,
  "profile_is_synthetic": true
}
```

</details>

---

#### `POST /api/v1/demo/inject-spoof` — Inject a forged packet

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Security demo: puts in the queue a packet signed with a wrong key. On arrival it is rejected and shows up with
`status = rejected`, `signature_valid = false`, in the log and in `/security/rejections`.

**SSE:** `packet.sent`, then `packet.rejected` on arrival.

**Răspuns 200:** [Packet](#packet)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>earth</code>)</summary>

```http
POST /api/v1/demo/inject-spoof
```

Răspuns `200`:

```json
{
  "id": "pk-0004",
  "seq": 3,
  "direction": "down",
  "kind": "weekly_summary",
  "status": "queued",
  "title": "Weekly summary · week 14",
  "sender": "Unknown sender",
  "level": null,
  "alert_status": null,
  "crew_id": null,
  "alert_id": null,
  "in_reply_to": null,
  "created_at": "2027-04-15T07:03:11.596788Z",
  "sent_at": null,
  "arrives_at": null,
  "delivered_at": null,
  "progress": 0.0,
  "eta_real_s": null,
  "signature_valid": null,
  "reject_reason": null,
  "size_bytes": 301
}
```

</details>

---

#### `POST /api/v1/demo/frozen-sensor` — Simulate a frozen sensor

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Security demo: a device sends the same value 20 times in a row; the validation layer rejects the last one.

**SSE:** `measurement.rejected`.

**Răspuns 200:** [Rejection](#rejection)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>medic</code>)</summary>

```http
POST /api/v1/demo/frozen-sensor
```

Răspuns `200`:

```json
{
  "id": "rj-0002",
  "at": "2027-04-15T07:03:23.592157Z",
  "kind": "frozen_sensor",
  "source": "wearable-cm-4",
  "crew_id": "cm-4",
  "metric_key": "temperature_c",
  "value": 36.6,
  "message": "The same value (36.6) 20 times in a row: frozen sensor."
}
```

</details>

---

#### `POST /api/v1/sim/reset` — Bring the demo back to the start

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Removes everything changed during the demo and reloads the scenario: the database is recreated, the history is
regenerated (same seed, so the same data), the clock restarts on day 96 at 07:00, and the account lockouts are
cleared. It takes a few seconds. Use it between rehearsals.

After a reset the frontend must reload everything (as after a reconnect). Tokens stay valid.

**SSE:** `mission.tick` with day 96, then `dashboard.changed`.

**Răspuns 200:** [Ok](#ok)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>medic</code>)</summary>

```http
POST /api/v1/sim/reset
```

Răspuns `200`:

```json
{
  "ok": true
}
```

</details>

---

### 13. Live events (SSE)

#### `GET /api/v1/events` — Live event stream

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

A Server-Sent Events connection, kept open while the app runs. **It replaces polling.**

* Authentication with the same `Authorization` header. The browser's `EventSource` cannot send headers, so use
  `@microsoft/fetch-event-source` (example in the README).
* Every user gets only the events they are allowed to see: an astronaut only their own and the general ones;
  `earth` only `mission.tick`, `environment.changed` and `packet.*`.
* `mission.tick` comes every real second; after 15 seconds without events a `: ping` comment keeps the
  connection open.
* On reconnect, reload the data of the current screen; missed events are not sent again.

The list of types and the shape of `data` for each: README, section "Live events".

**Răspuns 200:** flux `text/event-stream`

**Erori posibile:** 401, 422 — forma din secțiunea [Erori](#5-erori).

---


## 12. Modelele de date

Generate din `backend/app/schemas.py`. „Obligatoriu = nu” înseamnă că valoarea poate fi `null`.

### Enumerări (valori fixe)

#### Role

Rolul din JWT. Decide ce endpoint-uri sunt permise.

| Valoare | Înseamnă |
|---|---|
| `astronaut` | membru al echipajului, cu contul LUI; vede doar datele lui |
| `cmo` | ofițerul medical de la bord (Crew Medical Officer) |
| `earth` | medicul de zbor de pe Pământ |

#### Pillar

Cei patru piloni. Fiecare are o zonă pe corpul interactiv.

| Valoare | Înseamnă |
|---|---|
| `behavioral` | Tastatura  — creier |
| `cardio` | Inima      — inimă |
| `immune` | Santinela  — sistem imunitar |
| `musculoskeletal` | Încărcarea — oase și mușchi |

#### AlertTopic

Subiectul unei alerte: un pilon, radiațiile sau un semnal încrucișat.

| Valoare | Înseamnă |
|---|---|
| `behavioral` |  |
| `cardio` |  |
| `immune` |  |
| `musculoskeletal` |  |
| `radiation` |  |
| `cross_signal` |  |

#### Status

Semaforul. În UI: ok = verde ●, watch = galben ▲, alert = roșu ■, unknown = gri.

| Valoare | Înseamnă |
|---|---|
| `ok` | în limitele normalului personal |
| `watch` | abatere mică sau scurtă, de urmărit |
| `alert` | abatere peste prag |
| `unknown` | baseline-ul nu e gata sau lipsesc date |

#### EnvironmentId

| Valoare | Înseamnă |
|---|---|
| `iss` | stația spațială, orbită joasă |
| `moon_base` | bază pe Lună |
| `mars_transit` | nava, pe drumul spre Marte |
| `mars_base` | bază sau rover pe Marte |

#### Hazard

Cele 5 pericole NASA HRP.

| Valoare | Înseamnă |
|---|---|
| `radiation` | radiațiile spațiale |
| `isolation` | izolarea și spațiul închis |
| `distance` | distanța față de Pământ |
| `gravity` | gravitația modificată |
| `hostile_environment` | mediul închis și ostil al navei |

#### DataSource

De unde vine o valoare. `device` = semnată Ed25519; `manual` = tastată la check-in.

| Valoare | Înseamnă |
|---|---|
| `device` | de la un dispozitiv, semnată Ed25519 |
| `manual` | tastată de astronaut la check-in |
| `simulated` | generată de simulator; se afișează eticheta „date simulate” |

#### AlertState

| Valoare | Înseamnă |
|---|---|
| `active` | nouă, nimeni nu a confirmat-o |
| `acknowledged` | astronautul a văzut-o și lucrează la plan |
| `escalated` | urcată la nivelul 2 sau 3 |
| `resolved` | închisă (rezolvată / alarmă falsă) |

#### Cause

| Valoare | Înseamnă |
|---|---|
| `individual` | doar acest astronaut |
| `environmental` | mai mulți membri ai echipajului → probabil cabina |
| `unknown` |  |

#### PacketDirection

| Valoare | Înseamnă |
|---|---|
| `down` | navă → Pământ |
| `up` | Pământ → navă |

#### PacketKind

| Valoare | Înseamnă |
|---|---|
| `alert_l3` | alertă de nivel 3, navă → Pământ |
| `weekly_summary` | rezumat aprobat de astronaut, navă → Pământ |
| `earth_reply` | răspunsul medicului de zbor, Pământ → navă |
| `donki_alert` | avertizare de furtună solară, Pământ → navă |

#### PacketStatus

| Valoare | Înseamnă |
|---|---|
| `queued` | așteaptă fereastra de comunicare |
| `in_transit` | pe drum (întârzierea luminii) |
| `delivered` | ajuns, decriptat, semnătură validă |
| `rejected` | semnătură invalidă / replay / decriptare eșuată |

#### Verification

| Valoare | Înseamnă |
|---|---|
| `verified` | VERIFICAT în parameters.json |
| `unverified` | NEVERIFICAT — se afișează ca ipoteză |

#### Derivation

| Valoare | Înseamnă |
|---|---|
| `published` | valoare publicată în sursă |
| `derived` | prag ales/calculat de echipă |

#### RejectionKind

| Valoare | Înseamnă |
|---|---|
| `bad_signature` | semnătura nu se verifică |
| `implausible` | valoare în afara intervalului posibil |
| `frozen_sensor` | aceeași valoare de prea multe ori la rând |
| `replay` | pachet retrimis (seq deja văzut) |

### Obiecte

#### ErrorBody

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `code` | text | da | Cod stabil, pentru logică în frontend. Lista e în README, secțiunea Erori. Ex.: `"forbidden"` |
| `message` | text | da | Mesaj în română, gata de afișat utilizatorului. Ex.: `"Nu ai acces la datele altui membru al echipajului."` |
| `details` | obiect \| null | nu | Detalii opționale (ex. câmpurile invalide). |

#### ErrorResponse

Forma UNICĂ a oricărei erori (4xx/5xx).

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `error` | [ErrorBody](#errorbody) | da |  |

#### Ok

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `ok` | true/false | nu |  |

#### User

Un cont. FIECARE astronaut are contul lui; nu există cont comun de echipaj.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da |  Ex.: `"u-cm-2"` |
| `username` | text | da |  Ex.: `"specialist2"` |
| `display_name` | text | da |  Ex.: `"Specialist de misiune 2"` |
| `initials` | text | da |  Ex.: `"S2"` |
| `role` | [Role](#role) | da |  |
| `crew_id` | text \| null | nu | Membrul de echipaj al contului. Fiecare cont de astronaut are exact unul, diferit. `null` doar pentru rolul `earth`. Ex.: `"cm-2"` |

#### LoginAccount

Un cont afișat pe ecranul de autentificare (fără nicio dată medicală).

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `username` | text | da |  Ex.: `"specialist2"` |
| `display_name` | text | da |  Ex.: `"Specialist de misiune 2"` |
| `initials` | text | da |  Ex.: `"S2"` |
| `role` | [Role](#role) | da |  |
| `crew_id` | text \| null | nu |  Ex.: `"cm-2"` |
| `location` | `"ship"` \| `"earth"` | da | Pe ce stație de lucru apare contul: la bord sau la Controlul misiunii. |

#### LoginRequest

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `username` | text | da |  (lungime min 1; lungime max 40) Ex.: `"specialist2"` |
| `password` | text | da | Parola PERSONALĂ a contului. Fiecare cont are altă parolă. (lungime min 1; lungime max 256) Ex.: `"<parola din seed>"` |

#### LoginResponse

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `access_token` | text | da | JWT legat de acest cont. Se trimite la fiecare cerere: `Authorization: Bearer <token>`. |
| `token_type` | `"bearer"` | nu |  |
| `expires_in` | număr întreg | da | Secunde reale până la expirare. Ex.: `43200` |
| `user` | [User](#user) | da |  |

#### EnvironmentInfo

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | [EnvironmentId](#environmentid) | da |  |
| `name` | text | da |  Ex.: `"Tranzit spre Marte"` |
| `one_way_delay_s` | număr | da | Întârzierea legăturii într-un sens, în secunde de MISIUNE. Ex.: `700` |
| `gravity_g` | număr | da | Gravitația, în g. Ex.: `0.0` |
| `baseline_dose_usv_h` | număr | da | Rata de doză de fond pentru simulator, µSv/h. Ex.: `65.8` |
| `emphasized_hazards` | listă de [Hazard](#hazard) | da | Pericolele care contează cel mai mult în acest mediu. |
| `description` | text | da |  |

#### LinkStatus

Starea legăturii cu Pământul (pasul 3).

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `environment` | [EnvironmentId](#environmentid) | da |  |
| `one_way_delay_s` | număr | da | Secunde de misiune, într-un sens. Ex.: `700` |
| `one_way_delay_real_s` | număr | da | Aceeași întârziere în secunde REALE (delay / time_scale). Folosiți-o pentru animații. Ex.: `11.7` |
| `window_open` | true/false | da | Dacă fereastra de comunicare e deschisă acum. |
| `window_closes_at` | dată-oră (ISO 8601) \| null | nu |  |
| `next_window_at` | dată-oră (ISO 8601) \| null | nu | Când se redeschide fereastra, dacă e închisă. |
| `queued_down` | număr întreg | da | Pachete care așteaptă spre Pământ. Ex.: `1` |
| `queued_up` | număr întreg | da | Pachete care așteaptă spre navă. Ex.: `0` |

#### MissionState

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `name` | text | da |  Ex.: `"SHADOW-1"` |
| `sim_now` | dată-oră (ISO 8601) | da | Ora curentă a misiunii (SimClock). |
| `mission_day` | număr întreg | da | Ziua curentă a misiunii, de la 1. Ex.: `96` |
| `total_days` | număr întreg | da |  Ex.: `140` |
| `time_scale` | număr | da | De câte ori merge timpul misiunii mai repede decât cel real. Ex.: `60` |
| `environment` | [EnvironmentInfo](#environmentinfo) | da |  |
| `link` | [LinkStatus](#linkstatus) | da |  |

#### ClockUpdate

Trimiteți doar câmpul pe care vreți să-l schimbați.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `time_scale` | număr \| null | nu |  (min 1.0; max 86400.0) Ex.: `60` |
| `mission_day` | număr întreg \| null | nu | Sare ceasul la începutul acestei zile (doar pentru demo). (min 1.0) Ex.: `96` |

#### EnvironmentUpdate

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `environment` | [EnvironmentId](#environmentid) | da |  |

#### CrewMember

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da |  Ex.: `"cm-2"` |
| `display_name` | text | da |  Ex.: `"Specialist de misiune 2"` |
| `initials` | text | da |  Ex.: `"S2"` |
| `role_title` | text | da |  Ex.: `"Specialist de misiune"` |
| `is_cmo` | true/false | nu | Dacă e ofițerul medical de la bord. |

#### CrewSummary

Un rând din lista ofițerului medical. NU conține valori medicale, doar starea generală.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `member` | [CrewMember](#crewmember) | da |  |
| `overall_status` | [Status](#status) | da |  |
| `active_alerts` | număr întreg | da |  |
| `highest_level` | `1` \| `2` \| `3` \| null | nu |  |

#### SourceRef

O sursă științifică. Apare lângă orice prag, text sau recomandare.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `citation` | text | da |  Ex.: `"Alavi et al. (2022), Nature Medicine 28:175–184"` |
| `url` | text | da |  Ex.: `"https://www.nature.com/articles/s41591-021-01593-2"` |
| `verification` | [Verification](#verification) | nu |  |
| `derivation` | [Derivation](#derivation) | nu |  |
| `evidence_strength` | text \| null | nu | puternică / moderată / slabă / analog terestru / doar animale Ex.: `"moderată"` |

#### MetricValue

O valoare comparată cu baseline-ul PERSONAL al astronautului.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `key` | text | da | Cheie stabilă. Lista completă e în README, „Chei de metrici”. Ex.: `"night_pulse_bpm"` |
| `label` | text | da |  Ex.: `"Puls de noapte"` |
| `value` | număr \| null | da |  Ex.: `61.0` |
| `unit` | text | da |  Ex.: `"bpm"` |
| `baseline` | număr \| null | nu | Normalul personal din zbor. Ex.: `54.0` |
| `deviation_abs` | număr \| null | nu | value − baseline. Ex.: `7.0` |
| `deviation_pct` | număr \| null | nu |  Ex.: `13.0` |
| `status` | [Status](#status) | da |  |
| `source` | [DataSource](#datasource) | da |  |
| `measured_at` | dată-oră (ISO 8601) \| null | nu |  |

#### SeriesPoint

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `day` | număr întreg | da | Ziua misiunii. Ex.: `94` |
| `t` | dată-oră (ISO 8601) | da |  |
| `value` | număr \| null | da |  |
| `status` | [Status](#status) \| null | nu |  |

#### MetricSeries

Date pentru un grafic: valori pe zile + banda de baseline + pragul de alertă.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `metric_key` | text | da |  |
| `label` | text | da |  |
| `unit` | text | da |  |
| `baseline` | număr \| null | nu | Linia orizontală a normalului personal. |
| `band_low` | număr \| null | nu | Marginea de jos a benzii normale. |
| `band_high` | număr \| null | nu | Marginea de sus a benzii normale. |
| `threshold` | număr \| null | nu | Pragul de alertă, dacă există. |
| `threshold_label` | text \| null | nu |  Ex.: `"+4 bpm, 2 nopți (NightSignal)"` |
| `points` | listă de [SeriesPoint](#seriespoint) | da |  |

#### PerceptionGap

IDEEA CENTRALĂ: diferența dintre cum se simte astronautul și ce arată datele.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `self_reported_mood` | număr întreg \| null | nu | Răspunsul de la check-in. (min 1.0; max 5.0) |
| `self_score` | număr \| null | nu | Cum spune că se simte, pe 0–100. (min 0.0; max 100.0) Ex.: `80` |
| `objective_score` | număr \| null | nu | Ce arată datele obiective, pe 0–100. (min 0.0; max 100.0) Ex.: `52` |
| `gap` | număr \| null | nu | self_score − objective_score. Pozitiv = se simte mai bine decât arată datele. Ex.: `28` |
| `status` | [Status](#status) | da |  |
| `explanation` | text | da |  Ex.: `"Spui că ești bine (4/5), dar tastezi cu 18% mai lent și pulsul de noapte a crescut."` |
| `contributing_signals` | listă de text | nu |  Ex.: `["Tastare: −18% viteză", "Puls de noapte: +7 bpm"]` |

#### CrossSignal

Trei semnale slabe independente care, împreună, cântăresc mai mult.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da |  |
| `title` | text | da |  Ex.: `"Probabil debutul unei boli"` |
| `pillars` | listă de [Pillar](#pillar) | da |  |
| `signals` | listă de text | da |  |
| `confidence` | număr | da |  (min 0.0; max 1.0) Ex.: `0.72` |
| `explanation` | text | da |  |

#### Streak

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `key` | `"checkin"` \| `"split_training"` \| `"pvt"` | da |  |
| `label` | text | da |  Ex.: `"Check-in zilnic"` |
| `days` | număr întreg | da |  Ex.: `12` |
| `best` | număr întreg | da |  Ex.: `31` |

#### Reminder

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da |  |
| `kind` | `"checkin"` \| `"exercise"` \| `"pvt"` | da |  |
| `label` | text | da |  Ex.: `"A doua sesiune de exerciții"` |
| `due_at` | dată-oră (ISO 8601) | da |  |
| `done` | true/false | da |  |
| `overdue` | true/false | da | True = a trecut ora; în UI apare discret, nu ca alertă. |

#### AlertBrief

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da |  Ex.: `"al-1042"` |
| `crew_id` | text | da |  Ex.: `"cm-2"` |
| `topic` | [AlertTopic](#alerttopic) | da |  |
| `level` | `1` \| `2` \| `3` | da | 1 = te descurci singur, 2 = ofițerul medical, 3 = Pământul. |
| `status` | [Status](#status) | da | Culoarea alertei (watch sau alert). |
| `state` | [AlertState](#alertstate) | da |  |
| `title` | text | da |  Ex.: `"Puls de noapte +7 bpm, 3 nopți la rând"` |
| `created_at` | dată-oră (ISO 8601) | da |  |

#### PillarSummary

Un pilon, pe scurt: colorează zona de pe corp.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `pillar` | [Pillar](#pillar) | da |  |
| `name` | text | da | Numele din interfață. Ex.: `"Santinela"` |
| `body_zone` | `"brain"` \| `"heart"` \| `"immune"` \| `"bones"` | da | Zona de pe ilustrația corpului. |
| `status` | [Status](#status) | da |  |
| `score` | număr \| null | nu | 100 = exact ca baseline-ul personal. (min 0.0; max 100.0) Ex.: `64` |
| `headline` | text | da |  Ex.: `"Puls de noapte crescut 3 nopți la rând"` |
| `hazard` | [Hazard](#hazard) | da | Pericolul NASA principal pentru acest pilon. |
| `active_alert_id` | text \| null | nu |  |

#### Dashboard

Tot ce îi trebuie ecranului principal al astronautului, într-un singur apel.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `crew` | [CrewMember](#crewmember) | da |  |
| `as_of` | dată-oră (ISO 8601) | da |  |
| `mission_day` | număr întreg | da |  |
| `overall_status` | [Status](#status) | da |  |
| `pillars` | listă de [PillarSummary](#pillarsummary) | da | Mereu exact 4, în ordinea: behavioral, cardio, immune, musculoskeletal. |
| `perception_gap` | [PerceptionGap](#perceptiongap) | da |  |
| `cross_signals` | listă de [CrossSignal](#crosssignal) | da |  |
| `alerts_active_count` | număr întreg | da |  |
| `top_alert` | [AlertBrief](#alertbrief) \| null | nu | Alerta cea mai importantă, pentru banner. |
| `streaks` | listă de [Streak](#streak) | da |  |
| `reminders` | listă de [Reminder](#reminder) | da |  |
| `radiation_alert_active` | true/false | da | True = afișați banner-ul „Mergi în adăpost”. |
| `checkin_done_today` | true/false | da |  |

#### PlanStep

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da |  Ex.: `"st-1"` |
| `text` | text | da |  Ex.: `"Culcă-te cu o oră mai devreme în următoarele 3 nopți."` |
| `done` | true/false | nu |  |
| `done_at` | dată-oră (ISO 8601) \| null | nu |  |

#### PillarDetail

Panoul care se deschide la click pe o zonă a corpului.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `pillar` | [Pillar](#pillar) | da |  |
| `name` | text | da |  |
| `body_zone` | `"brain"` \| `"heart"` \| `"immune"` \| `"bones"` | da |  |
| `function_text` | text | da | Funcția părții corpului (cerință din brief). Max. 2 propoziții. |
| `hazard` | [Hazard](#hazard) | da |  |
| `hazard_text` | text | da | Rândul „Pericolul spațial”. |
| `status` | [Status](#status) | da |  |
| `score` | număr \| null | nu |  |
| `explanation` | text | da | Ce se întâmplă acum, în cuvinte simple. |
| `metrics` | listă de [MetricValue](#metricvalue) | da |  |
| `chart` | [MetricSeries](#metricseries) | da | Graficul principal al pilonului. |
| `plan_steps` | listă de [PlanStep](#planstep) | da | Pașii planului din alerta activă. Listă goală dacă nu e nicio alertă. |
| `active_alert_id` | text \| null | nu |  |
| `recheck_at` | dată-oră (ISO 8601) \| null | nu | Când se verifică dacă planul a funcționat (1–3 zile). |
| `sources` | listă de [SourceRef](#sourceref) | da |  |
| `limits_text` | text | da | „Limite oneste” — ce NU poate spune acest pilon. |
| `data_is_simulated` | true/false | da | True = afișați eticheta „date simulate”. |

#### TimelineDay

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `day` | număr întreg | da |  |
| `date` | dată-oră (ISO 8601) | da |  |
| `overall_status` | [Status](#status) | da |  |
| `pillars` | obiect {cheie: [Status](#status)} | da |  |
| `events` | listă de text | nu | Etichete scurte pentru derulator. Ex.: `["Furtună solară"]` |

#### Timeline

Date pentru derulatorul misiunii.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `crew_id` | text | da |  |
| `from_day` | număr întreg | da |  |
| `to_day` | număr întreg | da |  |
| `days` | listă de [TimelineDay](#timelineday) | da |  |

#### CheckinIndicator

Descrierea unui câmp din check-in. Frontend-ul construiește formularul din lista asta.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `key` | text | da |  Ex.: `"systolic_mmhg"` |
| `label` | text | da |  Ex.: `"Tensiunea (sistolică)"` |
| `unit` | text | da |  Ex.: `"mmHg"` |
| `input` | `"number"` \| `"scale_1_5"` \| `"choice"` | da |  |
| `min` | număr \| null | nu | Sub această valoare, câmpul e respins ca imposibil. |
| `max` | număr \| null | nu | Peste această valoare, câmpul e respins ca imposibil. |
| `step` | număr \| null | nu |  |
| `choices` | listă de text \| null | nu | Doar pentru input = choice. |
| `required` | true/false | nu |  |
| `how_to_measure` | text | da | Coloana „Cum se măsoară”. |
| `what_it_means` | text | da | Coloana „Ce înseamnă valoarea”. |
| `why_in_space` | text | da | Coloana „De ce contează în spațiu”. |
| `pillar` | [Pillar](#pillar) \| null | nu |  |
| `source` | [SourceRef](#sourceref) \| null | nu |  |

#### CheckinSchema

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `indicators` | listă de [CheckinIndicator](#checkinindicator) | da |  |

#### CheckinCreate

Check-in-ul de dimineață. Doar `mood` e obligatoriu; restul pot lipsi.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `mood` | număr întreg | da | Starea de spirit, 1 (foarte rău) – 5 (foarte bine). (min 1.0; max 5.0) Ex.: `4` |
| `systolic_mmhg` | număr \| null | nu |  Ex.: `112` |
| `diastolic_mmhg` | număr \| null | nu |  Ex.: `72` |
| `pulse_bpm` | număr \| null | nu | Puls în repaus, numărat 30 s × 2. Ex.: `58` |
| `glucose_mg_dl` | număr \| null | nu | Glicemie pe nemâncate. Ex.: `92` |
| `temperature_c` | număr \| null | nu |  Ex.: `36.9` |
| `sleep_hours` | număr \| null | nu |  Ex.: `5.5` |
| `meals_eaten` | `"all"` \| `"some"` \| `"none"` \| null | nu | „Ai mâncat toate mesele de ieri?” Ex.: `"some"` |
| `note` | text \| null | nu | Notă liberă. Textul se salvează; ritmul tastării se trimite separat la /keystrokes/batches. (lungime max 500) |

#### FieldRejection

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `field` | text | da |  Ex.: `"temperature_c"` |
| `value` | orice | da |  Ex.: `41.9` |
| `reason` | [RejectionKind](#rejectionkind) | da |  |
| `message` | text | da |  Ex.: `"Temperatura 41,9 °C e în afara intervalului posibil. Măsoară din nou."` |

#### Checkin

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da |  Ex.: `"ck-0096"` |
| `crew_id` | text | da |  |
| `mission_day` | număr întreg | da |  |
| `created_at` | dată-oră (ISO 8601) | da |  |
| `values` | [CheckinCreate](#checkincreate) | da | Valorile ACCEPTATE. Câmpurile respinse sunt `null` aici. |

#### CheckinResult

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `checkin` | [Checkin](#checkin) | da |  |
| `rejected` | listă de [FieldRejection](#fieldrejection) | da | Câmpurile respinse la validare. Lista goală = totul a fost acceptat. |
| `perception_gap` | [PerceptionGap](#perceptiongap) | da | Recalculat imediat după check-in. |
| `alerts_created` | listă de [AlertBrief](#alertbrief) | da |  |
| `streak` | [Streak](#streak) | da |  |
| `message` | text | da | Mesaj scurt de confirmare pentru UI. Ex.: `"Check-in salvat. 12 zile la rând."` |

#### KeyEvent

O apăsare de tastă. NU conține litera, doar timpii și clasa tastei.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `t_down_ms` | număr | da | `performance.now()` la keydown, ms. Ex.: `10234.5` |
| `t_up_ms` | număr | da | `performance.now()` la keyup, ms. Ex.: `10321.1` |
| `key_class` | `"char"` \| `"space"` \| `"backspace"` \| `"enter"` \| `"other"` | da | Clasa tastei. NICIODATĂ caracterul propriu-zis. |

#### KeystrokeBatch

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `session_id` | text | da | UUID generat de frontend la începutul unei sesiuni de scris. Ex.: `"8b1f0c1e-6f0a-4f0e-9d53-2c1a7f1b9e10"` |
| `context` | `"free_typing"` \| `"checkin_note"` \| `"ai_chat"` \| `"demo"` | da | Unde a tastat. |
| `events` | listă de [KeyEvent](#keyevent) | da | Trimiteți loturi de max. 2000 de evenimente, la ~5 secunde. (min elemente 1; max elemente 2000) |

#### KeystrokeFeatures

Trăsăturile calculate. hold = apăsare→eliberare; flight = apăsare→apăsarea următoare.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `hold_ms_mean` | număr | da |  Ex.: `96.4` |
| `hold_ms_sd` | număr | da |  Ex.: `21.3` |
| `flight_ms_mean` | număr | da |  Ex.: `182.0` |
| `flight_ms_sd` | număr | da |  Ex.: `64.9` |
| `backspace_rate` | număr | da | Backspace-uri / total taste, 0–1. Ex.: `0.06` |
| `keys_per_min` | număr | da |  Ex.: `214` |
| `n_keys` | număr întreg | da |  Ex.: `380` |

#### KeystrokeResult

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `session_id` | text | da |  |
| `features` | [KeystrokeFeatures](#keystrokefeatures) | da |  |
| `baseline` | [KeystrokeFeatures](#keystrokefeatures) \| null | nu | `null` până când baseline-ul e gata. |
| `deviation_z` | obiect {cheie: număr} | da | Abaterea fiecărei trăsături, în deviații standard personale. Ex.: `{"hold_ms_mean": 1.9, "keys_per_min": -1.6}` |
| `fatigue_index` | număr \| null | nu | 0 = ca baseline-ul, 100 = abatere maximă. (min 0.0; max 100.0) Ex.: `68` |
| `status` | [Status](#status) | da |  |
| `baseline_ready` | true/false | da |  |
| `baseline_sessions` | număr întreg | da | Câte sesiuni au intrat în baseline până acum. Ex.: `9` |

#### KeystrokeSessionPoint

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `session_id` | text | da |  |
| `at` | dată-oră (ISO 8601) | da |  |
| `keys_per_min` | număr | da |  |
| `hold_ms_mean` | număr | da |  |
| `fatigue_index` | număr \| null | nu |  |
| `status` | [Status](#status) | da |  |

#### KeystrokeSummary

Pentru barele live de tastare și comparația „ora 2 vs ora 18” din demo.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `baseline` | [KeystrokeFeatures](#keystrokefeatures) \| null | da |  |
| `current` | [KeystrokeFeatures](#keystrokefeatures) \| null | da |  |
| `fatigue_index` | număr \| null | nu |  |
| `status` | [Status](#status) | da |  |
| `baseline_ready` | true/false | da |  |
| `sessions` | listă de [KeystrokeSessionPoint](#keystrokesessionpoint) | da |  |

#### PvtTrial

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `stimulus_at_ms` | număr | da | Când a apărut stimulul, ms de la începutul testului. |
| `rt_ms` | număr \| null | nu | Timpul de reacție. `null` = nu a răspuns. Ex.: `287` |
| `false_start` | true/false | nu | A apăsat înainte de stimul. |

#### PvtSubmit

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `started_at` | dată-oră (ISO 8601) | da |  |
| `duration_s` | număr întreg | nu | PVT-B durează 3 minute. (min 1.0; max 3600.0) |
| `trials` | listă de [PvtTrial](#pvttrial) | da |  (min elemente 1; max elemente 1000) |

#### PvtResult

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da |  Ex.: `"pvt-0031"` |
| `crew_id` | text | da |  |
| `at` | dată-oră (ISO 8601) | da |  |
| `n_trials` | număr întreg | da |  |
| `mean_rt_ms` | număr | da |  Ex.: `312.5` |
| `mean_speed` | număr | da | Media 1/RT în 1/s — metrica cea mai sensibilă (Basner 2011). Ex.: `3.31` |
| `lapses` | număr întreg | da | Răspunsuri cu RT ≥ 355 ms. Ex.: `6` |
| `false_starts` | număr întreg | da |  |
| `baseline_speed` | număr \| null | nu |  Ex.: `3.72` |
| `deviation_sd` | număr \| null | nu | Abaterea vitezei față de baseline, în SD. Prag derivat: −1,24. Ex.: `-1.4` |
| `status` | [Status](#status) | da |  |

#### ExerciseSet

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `exercise` | text | da |  (lungime max 80) Ex.: `"genuflexiuni ARED"` |
| `reps` | număr întreg | da |  (min 1.0; max 1000.0) Ex.: `10` |
| `load_kg` | număr | da |  (min 0.0; max 2000.0) Ex.: `85` |

#### ExerciseSessionCreate

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `kind` | `"resistance"` \| `"aerobic"` | da |  |
| `started_at` | dată-oră (ISO 8601) | da |  |
| `duration_min` | număr | da |  (max 1440.0; > 0.0) Ex.: `40` |
| `sets` | listă de [ExerciseSet](#exerciseset) | nu | Gol pentru sesiuni aerobe. (max elemente 200) |

#### ExerciseSession

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `kind` | `"resistance"` \| `"aerobic"` | da |  |
| `started_at` | dată-oră (ISO 8601) | da |  |
| `duration_min` | număr | da |  (max 1440.0; > 0.0) Ex.: `40` |
| `sets` | listă de [ExerciseSet](#exerciseset) | nu | Gol pentru sesiuni aerobe. (max elemente 200) |
| `id` | text | da |  Ex.: `"ex-0211"` |
| `crew_id` | text | da |  |
| `mission_day` | număr întreg | da |  |
| `loading_score` | număr | da | Stimulul de încărcare osoasă al sesiunii. Ex.: `38` |
| `source` | [DataSource](#datasource) | da |  |

#### BoneProjection

Estimare, NU măsurătoare: densitatea osoasă nu se poate măsura la bord.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `current_plan_pct_month` | număr | da | Pierderea estimată de densitate cu planul actual, % pe lună. Ex.: `-0.64` |
| `split_plan_pct_month` | număr | da | Aceeași estimare cu antrenamentul împărțit (ipoteză, doar pe animale). Ex.: `-0.45` |
| `note` | text | da |  |

#### ExerciseToday

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `mission_day` | număr întreg | da |  |
| `planned_sessions` | număr întreg | da |  Ex.: `2` |
| `completed_sessions` | număr întreg | da |  Ex.: `1` |
| `loading_score` | număr | da | Scorul zilnic de încărcare. (min 0.0) Ex.: `38` |
| `loading_target` | număr | da |  Ex.: `80` |
| `split_recommended` | true/false | da |  |
| `recommendation_text` | text | da |  Ex.: `"Împarte antrenamentul de azi în două sesiuni, la câteva ore distanță."` |
| `streak` | [Streak](#streak) | da |  |
| `sessions` | listă de [ExerciseSession](#exercisesession) | da |  |
| `projection` | [BoneProjection](#boneprojection) | da |  |

#### Evidence

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `metric_key` | text | da |  |
| `label` | text | da |  |
| `value` | număr \| null | da |  |
| `unit` | text | da |  |
| `baseline` | număr \| null | nu |  |
| `deviation_text` | text | da |  Ex.: `"+7 bpm peste mediana personală, 3 nopți"` |

#### Recommendation

O intrare din catalogul scris de echipă pe baza NASA. AI-ul doar o reformulează.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da | Format: <topic>-<nivel>-<nr>, ex. `immune-2-1`. Ex.: `"immune-2-1"` |
| `topic` | [AlertTopic](#alerttopic) | da |  |
| `level` | `1` \| `2` \| `3` | da |  |
| `trigger` | text | da | Când se aplică. |
| `action` | text | da | Ce are de făcut. |
| `hrp_risk` | text | da | Riscul NASA HRP corespunzător. |
| `hrp_risk_url` | text | da |  |
| `source` | [SourceRef](#sourceref) | da |  |

#### AlertHistoryEntry

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `at` | dată-oră (ISO 8601) | da |  |
| `actor` | text | da |  Ex.: `"Specialist de misiune 2"` |
| `role` | [Role](#role) \| null | nu |  |
| `action` | `"created"` \| `"acknowledged"` \| `"step_done"` \| `"escalated"` \| `"packet_sent"` \| `"earth_replied"` \| `"rechecked"` \| `"resolved"` | da |  |
| `note` | text \| null | nu |  |

#### Alert

Alerta completă.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da |  Ex.: `"al-1042"` |
| `crew_id` | text | da |  Ex.: `"cm-2"` |
| `topic` | [AlertTopic](#alerttopic) | da |  |
| `level` | `1` \| `2` \| `3` | da | 1 = te descurci singur, 2 = ofițerul medical, 3 = Pământul. |
| `status` | [Status](#status) | da | Culoarea alertei (watch sau alert). |
| `state` | [AlertState](#alertstate) | da |  |
| `title` | text | da |  Ex.: `"Puls de noapte +7 bpm, 3 nopți la rând"` |
| `created_at` | dată-oră (ISO 8601) | da |  |
| `explanation` | text | da | Ce s-a observat, în cuvinte simple. |
| `cause` | [Cause](#cause) | da |  |
| `cause_explanation` | text | da |  Ex.: `"Doar tu ai această abatere; ceilalți membri ai echipajului sunt în limite."` |
| `evidence` | listă de [Evidence](#evidence) | da |  |
| `recommendation` | [Recommendation](#recommendation) | da |  |
| `plan_steps` | listă de [PlanStep](#planstep) | da |  |
| `recheck_at` | dată-oră (ISO 8601) \| null | nu | Când verifică SHADOW dacă planul a funcționat. |
| `packet_id` | text \| null | nu | Pachetul spre Pământ, dacă alerta a ajuns la nivelul 3. |
| `earth_reply` | text \| null | nu | Răspunsul medicului de pe Pământ, după ce a sosit. |
| `history` | listă de [AlertHistoryEntry](#alerthistoryentry) | da |  |

#### StepUpdate

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `done` | true/false | da |  |

#### EscalateRequest

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `to_level` | `2` \| `3` | da | 2 = către ofițerul medical; 3 = către Pământ (doar rolul cmo). |
| `note` | text \| null | nu |  (lungime max 500) |

#### ResolveRequest

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `outcome` | `"resolved"` \| `"false_alarm"` \| `"monitoring"` | da |  |
| `note` | text \| null | nu |  (lungime max 500) |

#### Packet

Un mesaj din coada navă ↔ Pământ. Conținutul e criptat; aici e doar plicul.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da |  Ex.: `"pk-0007"` |
| `seq` | număr întreg | da | Număr de ordine unic; blochează retrimiterea (replay). Ex.: `7` |
| `direction` | [PacketDirection](#packetdirection) | da |  |
| `kind` | [PacketKind](#packetkind) | da |  |
| `status` | [PacketStatus](#packetstatus) | da |  |
| `title` | text | da | Titlu scurt, vizibil în coadă. Ex.: `"Imunitar · puls de noapte +7 bpm, 3 nopți"` |
| `sender` | text | da |  Ex.: `"Ofițer medical de bord"` |
| `level` | `1` \| `2` \| `3` \| null | nu |  |
| `alert_status` | [Status](#status) \| null | nu | Culoarea alertei din pachet, dacă e cazul. |
| `crew_id` | text \| null | nu |  |
| `alert_id` | text \| null | nu |  |
| `in_reply_to` | text \| null | nu | Id-ul pachetului la care răspunde. |
| `created_at` | dată-oră (ISO 8601) | da |  |
| `sent_at` | dată-oră (ISO 8601) \| null | nu | Când a plecat (s-a deschis fereastra). |
| `arrives_at` | dată-oră (ISO 8601) \| null | nu | Când ajunge. `sent_at + one_way_delay`. |
| `delivered_at` | dată-oră (ISO 8601) \| null | nu |  |
| `progress` | număr | da | 0 = încă în coadă, 1 = ajuns. Pentru bara de progres. (min 0.0; max 1.0) Ex.: `0.64` |
| `eta_real_s` | număr \| null | nu | Secunde REALE până la sosire. Ex.: `4.2` |
| `signature_valid` | true/false \| null | nu | `null` până la sosire. False = pachet respins. |
| `reject_reason` | [RejectionKind](#rejectionkind) \| null | nu |  |
| `size_bytes` | număr întreg | da |  Ex.: `1840` |

#### PacketCrypto

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `cipher` | text | nu |  |
| `signature_alg` | text | nu |  |
| `key_id` | text | da |  Ex.: `"ship-2026-01"` |
| `nonce_b64` | text | da |  |
| `signature_b64` | text | da |  |

#### PacketDetail

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da |  Ex.: `"pk-0007"` |
| `seq` | număr întreg | da | Număr de ordine unic; blochează retrimiterea (replay). Ex.: `7` |
| `direction` | [PacketDirection](#packetdirection) | da |  |
| `kind` | [PacketKind](#packetkind) | da |  |
| `status` | [PacketStatus](#packetstatus) | da |  |
| `title` | text | da | Titlu scurt, vizibil în coadă. Ex.: `"Imunitar · puls de noapte +7 bpm, 3 nopți"` |
| `sender` | text | da |  Ex.: `"Ofițer medical de bord"` |
| `level` | `1` \| `2` \| `3` \| null | nu |  |
| `alert_status` | [Status](#status) \| null | nu | Culoarea alertei din pachet, dacă e cazul. |
| `crew_id` | text \| null | nu |  |
| `alert_id` | text \| null | nu |  |
| `in_reply_to` | text \| null | nu | Id-ul pachetului la care răspunde. |
| `created_at` | dată-oră (ISO 8601) | da |  |
| `sent_at` | dată-oră (ISO 8601) \| null | nu | Când a plecat (s-a deschis fereastra). |
| `arrives_at` | dată-oră (ISO 8601) \| null | nu | Când ajunge. `sent_at + one_way_delay`. |
| `delivered_at` | dată-oră (ISO 8601) \| null | nu |  |
| `progress` | număr | da | 0 = încă în coadă, 1 = ajuns. Pentru bara de progres. (min 0.0; max 1.0) Ex.: `0.64` |
| `eta_real_s` | număr \| null | nu | Secunde REALE până la sosire. Ex.: `4.2` |
| `signature_valid` | true/false \| null | nu | `null` până la sosire. False = pachet respins. |
| `reject_reason` | [RejectionKind](#rejectionkind) \| null | nu |  |
| `size_bytes` | număr întreg | da |  Ex.: `1840` |
| `payload` | obiect \| null | nu | Conținutul DECRIPTAT. Apare doar dacă pachetul e `delivered` și rolul are voie să-l citească. |
| `crypto` | [PacketCrypto](#packetcrypto) | da |  |

#### OutboxCreate

Astronautul/ofițerul medical pune ceva în coada spre Pământ.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `kind` | `"weekly_summary"` \| `"alert_l3"` | da | `alert_l3`: doar ofițerul medical, doar pentru o alertă deja escaladată la nivelul 3. |
| `crew_id` | text | da |  Ex.: `"cm-2"` |
| `alert_id` | text \| null | nu | Obligatoriu pentru kind = alert_l3. |
| `body` | text \| null | nu | Text liber adăugat de expeditor. (lungime max 2000) |

#### EarthReplyCreate

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `in_reply_to` | text \| null | nu | Id-ul pachetului la care răspunde. Ex.: `"pk-0007"` |
| `crew_id` | text | da |  Ex.: `"cm-2"` |
| `alert_id` | text \| null | nu |  Ex.: `"al-1042"` |
| `body` | text | da |  (lungime min 1; lungime max 2000) Ex.: `"De acord cu odihna. Temperatura de două ori pe zi."` |

#### CrewMessage

Un mesaj SOSIT la bord de pe Pământ (deja decriptat și verificat).

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `packet_id` | text | da |  |
| `kind` | `"earth_reply"` \| `"donki_alert"` | da |  |
| `sender` | text | da |  Ex.: `"Medicul de zbor"` |
| `body` | text | da |  |
| `sent_at` | dată-oră (ISO 8601) | da |  |
| `delivered_at` | dată-oră (ISO 8601) | da |  |
| `alert_id` | text \| null | nu |  |
| `donki_event_id` | text \| null | nu |  |
| `read` | true/false | nu |  |

#### SepEvent

Evenimentul real de particule solare din NASA DONKI folosit în simulator.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `donki_id` | text | da |  Ex.: `"2024-05-11T02:10:00-SEP-001"` |
| `event_time` | dată-oră (ISO 8601) | da | Ora reală a evenimentului (2024). |
| `sim_onset_at` | dată-oră (ISO 8601) \| null | nu | Când lovește în timpul misiunii simulate. |
| `instrument` | text | da |  Ex.: `"GOES-P: SEISS >100 MeV"` |
| `flare_class` | text | da |  Ex.: `"X5.8"` |
| `cme_id` | text | da |  Ex.: `"2024-05-11T01:36:00-CME-001"` |
| `donki_url` | text | da |  |
| `note` | text | da |  Ex.: `"GLE 74, furtuna Gannon (mai 2024)"` |

#### RadiationStatus

Starea radiațiilor acum (pasul 4). Prototipul afișează totul în Sv, simplificat.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `at` | dată-oră (ISO 8601) | da |  |
| `dose_rate_usv_h` | număr | da | Rata de doză la dozimetrul de la bord, µSv/h. Ex.: `412.0` |
| `mean_24h_usv_h` | număr | da | Media mobilă pe 24 h. Ex.: `66.0` |
| `ratio` | număr | da | dose_rate / mean_24h. Ex.: `6.2` |
| `threshold_ratio` | număr | nu | Pragul de alertă (derivat de echipă). |
| `alert_active` | true/false | da |  |
| `alert_id` | text \| null | nu |  |
| `sheltered` | true/false | da |  |
| `sheltered_since` | dată-oră (ISO 8601) \| null | nu |  |
| `event` | [SepEvent](#sepevent) \| null | nu | `null` dacă nu rulează nicio furtună. |
| `event_dose_msv` | număr | da | Doza acumulată de la începutul evenimentului, mSv. Ex.: `1.8` |
| `onboard_alert_at` | dată-oră (ISO 8601) \| null | nu | Când a dat SHADOW alerta, din dozimetru. |
| `earth_warning_arrived_at` | dată-oră (ISO 8601) \| null | nu | Când a sosit avertizarea DONKI de pe Pământ. |
| `lead_minutes` | număr \| null | nu | Cu câte minute de misiune a fost SHADOW mai rapid decât Pământul. `null` până sosește avertizarea. Ex.: `31.0` |
| `profile_is_synthetic` | true/false | nu | Forma curbei e sintetică; ora evenimentului e reală. Afișați eticheta. |

#### RadiationPoint

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `t` | dată-oră (ISO 8601) | da |  |
| `dose_rate_usv_h` | număr | da |  |
| `mean_24h_usv_h` | număr | da |  |
| `sheltered` | true/false | nu |  |

#### RadiationSeries

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `unit` | text | nu |  |
| `threshold_ratio` | număr | nu |  |
| `points` | listă de [RadiationPoint](#radiationpoint) | da |  |

#### ShelterAck

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `sheltered` | true/false | da | True = „Sunt în adăpost”. False = a ieșit din adăpost. |

#### SepStart

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `event_id` | text | nu |  (lungime max 80) |
| `starts_in_min` | număr | nu | Peste câte minute de MISIUNE începe furtuna. (min 0.0; max 100000.0) |

#### ChatMessage

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `role` | `"user"` \| `"assistant"` | da |  |
| `content` | text | da |  (lungime max 2000) |

#### AiChatRequest

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `crew_id` | text | da |  Ex.: `"cm-2"` |
| `message` | text | da |  (lungime min 1; lungime max 1000) Ex.: `"De ce mi-a crescut pulsul de noapte?"` |
| `alert_id` | text \| null | nu | Dacă întrebarea e despre o alertă anume. Ex.: `"al-1042"` |
| `history` | listă de [ChatMessage](#chatmessage) | nu | Ultimele max. 6 mesaje sunt folosite. (max elemente 20) |

#### Citation

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `title` | text | da |  Ex.: `"NASA HRP — Risk of Altered Immune Response"` |
| `url` | text | da |  |
| `snippet` | text | da | Fragmentul din document pe care se bazează răspunsul. |

#### AiChatResponse

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `answer` | text | da |  |
| `citations` | listă de [Citation](#citation) | da | Sursele NASA. Dacă lista e goală, afișați „fără sursă”. |
| `recommendation_ids` | listă de text | da | Intrările din catalog pe care le reformulează răspunsul. Ex.: `["immune-2-1"]` |
| `model` | text | da |  Ex.: `"gemma-3-4b-it-Q4_K_M"` |
| `latency_ms` | număr întreg | da |  |
| `fallback` | true/false | da | True = modelul nu a răspuns; textul vine direct din catalog. |
| `disclaimer` | text | nu |  |

#### AiStatus

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `ready` | true/false | da |  |
| `model` | text \| null | nu |  |
| `mode` | `"local"` \| `"colab_simulation"` \| `"fallback"` \| `"mock"` | da | Unde rulează modelul: `local` (laptopul de demo), `colab_simulation` (Colab, prezentat deschis ca simulare), `fallback` (serviciul nu răspunde; doar catalogul), `mock` (serviciul AI încă fără model). Afișați-l onest în UI. |

#### AccessLogEntry

Jurnalul de acces: doar se adaugă, fiecare intrare conține hash-ul celei dinainte.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | număr întreg | da |  |
| `at` | dată-oră (ISO 8601) | da |  |
| `actor` | text | da |  Ex.: `"Ofițer medical de bord"` |
| `actor_role` | [Role](#role) | da |  |
| `action` | text | da | login, login_failed, logout, read_dashboard, read_pillar, read_alert, escalate, read_packet, … Ex.: `"read_alert"` |
| `resource` | text | da |  Ex.: `"alerts/al-1042"` |
| `crew_id` | text \| null | nu |  |
| `outcome` | `"allowed"` \| `"denied"` | da |  |
| `prev_hash` | text | da |  |
| `hash` | text | da |  |

#### AccessLogIntegrity

Rezultatul verificării lanțului de hash-uri al jurnalului de acces, făcută la cerere.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `intact` | true/false | da | `false` = o intrare a fost modificată sau ștearsă în afara aplicației. |
| `entries` | număr întreg | da | Câte intrări are tot jurnalul (nu doar cele pe care le vede contul). Ex.: `42` |
| `checked_at` | dată-oră (ISO 8601) | da | Când s-a făcut verificarea (timpul misiunii). |

#### Rejection

O valoare sau un pachet respins de stratul de securitate.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da |  Ex.: `"rj-0003"` |
| `at` | dată-oră (ISO 8601) | da |  |
| `kind` | [RejectionKind](#rejectionkind) | da |  |
| `source` | text | da | Dispozitivul sau pachetul. Ex.: `"senzor-07"` |
| `crew_id` | text \| null | nu |  |
| `metric_key` | text \| null | nu |  |
| `value` | număr \| null | nu |  |
| `message` | text | da |  Ex.: `"Temperatură 41,9 °C · semnătură invalidă"` |

#### MeasurementIngest

O măsurătoare trimisă de un dispozitiv (sau de simulator), semnată Ed25519.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `device_id` | text | da |  (lungime min 1; lungime max 40) Ex.: `"wearable-cm-2"` |
| `crew_id` | text | da |  (lungime min 1; lungime max 16) Ex.: `"cm-2"` |
| `metric_key` | text | da |  (lungime min 1; lungime max 40) Ex.: `"night_pulse_bpm"` |
| `value` | număr | da |  Ex.: `61` |
| `unit` | text | da |  (lungime max 16) Ex.: `"bpm"` |
| `measured_at` | dată-oră (ISO 8601) | da |  |
| `signature_b64` | text | da | Ed25519 peste JSON-ul canonic al celorlalte câmpuri (chei sortate, fără spații). (lungime max 200) |

#### IngestResult

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `accepted` | true/false | da |  |
| `rejection` | [Rejection](#rejection) \| null | nu |  |

#### TestCase

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `name` | text | da |  Ex.: `"test_nightsignal_red_after_two_nights"` |
| `module` | text | da |  Ex.: `"tests/test_immune.py"` |
| `outcome` | `"passed"` \| `"failed"` \| `"skipped"` | da |  |
| `duration_ms` | număr | da |  |

#### TestReport

Rezultatul pytest pe motorul de protocoale, pentru ecranul Evidence.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `ran_at` | dată-oră (ISO 8601) | da |  |
| `passed` | număr întreg | da |  |
| `failed` | număr întreg | da |  |
| `skipped` | număr întreg | nu |  |
| `duration_s` | număr | da |  |
| `tests` | listă de [TestCase](#testcase) | da |  |

#### Parameter

Un prag din parameters.json, cu sursa lui.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da |  Ex.: `"nightsignal_red_delta_bpm"` |
| `topic` | text | da |  Ex.: `"imunitar"` |
| `name` | text | da |  |
| `value` | orice | da |  |
| `unit` | text | da |  |
| `explanation` | text | da |  |
| `is_key_threshold` | true/false | da | True = motorul de triaj îl folosește direct. |
| `source` | [SourceRef](#sourceref) | da |  |

#### MissionTick

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `sim_now` | dată-oră (ISO 8601) | da |  |
| `mission_day` | număr întreg | da |  |

#### SseEvent

Plicul oricărui eveniment de pe /events. `data` depinde de `type` — vezi README, secțiunea SSE.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da |  Ex.: `"ev-000123"` |
| `type` | `"mission.tick"` \| `"environment.changed"` \| `"alert.created"` \| `"alert.updated"` \| `"packet.sent"` \| `"packet.arrived"` \| `"packet.rejected"` \| `"radiation.alert"` \| `"radiation.reading"` \| `"radiation.cleared"` \| `"measurement.rejected"` \| `"reminder.due"` \| `"dashboard.changed"` | da |  |
| `at` | dată-oră (ISO 8601) | da |  |
| `crew_id` | text \| null | nu | Dacă evenimentul privește un singur membru. |
| `data` | obiect | da |  |

