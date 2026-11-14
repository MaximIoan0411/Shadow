# SHADOW — contractul API (frontend ↔ backend)

**NASA Space Apps 2026 · versiunea {{VERSION}} · {{N_OPS}} endpoint-uri · {{N_MODELS}} modele**

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

{{REF_TOC}}

{{REFERENCE}}

## 12. Modelele de date

Generate din `backend/app/schemas.py`. „Obligatoriu = nu” înseamnă că valoarea poate fi `null`.

{{MODELS}}
