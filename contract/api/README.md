# SHADOW — contractul API (frontend ↔ backend)

**NASA Space Apps 2026 · versiunea 1.2.0 · 57 endpoint-uri · 97 modele**

Acest document este **înțelegerea dintre frontend și backend**. Dacă amândouă părțile îl respectă, se pot construi
separat și se potrivesc la integrare. Tot ce e aici rulează deja: scheletul din `backend/` este un **server mock**
care răspunde la toate endpoint-urile cu date de exemplu valide, iar textele, mediile, catalogul și pragurile vin
deja din `data/`.

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
> tokenurile mock sunt acum `mock-specialist2`, `mock-medic` etc. Detalii: secțiunea 4.

## Ce citești, în funcție de ce faci

| Dacă lucrezi la… | Citește | Apoi |
|---|---|---|
| **Frontend** | secțiunile 1–7 și 10 | pornește mock-ul, generează tipurile TypeScript, construiește pe datele mock |
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

**Conturi de test — câte unul pentru fiecare astronaut.** Fiecare are altă parolă (valorile de test sunt și în
`backend/app/examples.py`, la `MOCK_PASSWORDS`):

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
# → {"access_token":"mock-specialist2", "user": {"role":"astronaut","crew_id":"cm-2", ...}}

curl -s localhost:8000/api/v1/crew/cm-2/dashboard -H 'Authorization: Bearer mock-specialist2'   # 200, datele lui
curl -s localhost:8000/api/v1/crew/cm-2/dashboard -H 'Authorization: Bearer mock-comandant'     # 403, nu sunt ale lui
```

Scenariul mock: **ziua 96 din 140, ora 07:00, tranzit spre Marte**. Misiunea pornește din acest punct; zilele 1–95
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
├── examples.py              ← datele mock (scenariul zilei 96); dispare pe măsură ce apare logica reală
├── datafiles.py             ← formatul fișierelor din data/ + încărcarea lor
├── ai_schemas.py            ← copie a ai/service/schemas.py
└── security/                ← al echipei de securitate (variante provizorii, semnături finale)

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

**În mock**, tokenul este textul `mock-<utilizator>` (de exemplu `mock-specialist2`), ca să puteți testa fără
login, și nu se revocă la `logout`.

### Ce are voie fiecare rol

| Resursă | `astronaut` | `cmo` | `earth` |
|---|---|---|---|
| Datele proprii (`/crew/{id}/…` cu `crew_id`-ul contului) | da | da | — |
| Datele altui membru (`/crew/{alt_id}/…`) | **nu (403)**, nici comandantul | da, se scrie în jurnal | nu (403) |
| Alertele proprii | toate | toate | — |
| Alertele altui membru | nu | doar nivelul 2 și 3 | doar ce ajunge prin pachete |
| Escaladare la nivelul 2 | da | da | nu |
| Escaladare la nivelul 3 | **nu** | da | nu |
| Coada de pachete | nu | da | da |
| Răspuns de pe Pământ (`/earth/replies`) | nu | nu | da |
| Dozimetrul în timp real (`/radiation/status`) | da | da | **nu** |
| Jurnalul de acces | doar accesul la datele lui | tot | nu |
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
| `mission.tick` | la ~1 secundă reală (mock: la 3 s) | [MissionTick](#missiontick) | actualizează ceasul și ziua misiunii |
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
- `GET /security/rejections` — valori și pachete respinse.
- `POST /demo/frozen-sensor` — demo cu senzor înghețat → SSE `measurement.rejected`.
- `GET /evidence/tests` — rezultatele testelor automate.
- `GET /evidence/parameters` — pragurile din `parameters.json`, fiecare cu sursa lui.

## 8. Cine implementează ce

Contractul fixează **ce** se vede din afară. **Cum** se construiește backend-ul (straturi, bază de date asincronă,
pornire din ziua 96, task-uri din fundal, ordinea pe ore) e în `backend/PLAN_DE_ATAC_BACKEND.md`, iar lista
funcționalităților, în `BACKEND_SARCINI.md`. Pe scurt:

| Modul | Unde | Ce înlocuiește mock-ul |
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

Generată din cod. Exemplele sunt **răspunsuri reale ale serverului mock**; listele lungi sunt scurtate.

- [0. Sănătatea serverului](#0-sănătatea-serverului)
- [1. Autentificare](#1-autentificare)
- [2. Misiune, mediu, ceas](#2-misiune-mediu-ceas)
- [3. Echipaj și corpul interactiv](#3-echipaj-și-corpul-interactiv)
- [4. Check-in](#4-check-in)
- [5. Tastare și test de reacție](#5-tastare-și-test-de-reacție)
- [6. Exerciții](#6-exerciții)
- [7. Alerte, triaj, catalog](#7-alerte-triaj-catalog)
- [8. Legătura cu Pământul](#8-legătura-cu-pământul)
- [9. Radiații și furtuna solară](#9-radiații-și-furtuna-solară)
- [10. Medicul AI](#10-medicul-ai)
- [11. Securitate și dovezi](#11-securitate-și-dovezi)
- [12. Demo și simulator](#12-demo-și-simulator)
- [13. Evenimente live (SSE)](#13-evenimente-live-sse)

### 0. Sănătatea serverului

#### `GET /health` — Serverul răspunde?

**Cine poate apela:** oricine, fără autentificare

Fără autentificare. Folosit de Docker Compose și de frontend la pornire.
`mode` e `mock` cât timp există endpoint-uri pe date de exemplu, apoi `real`.

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
  "mode": "mock"
}
```

</details>

---

### 1. Autentificare

#### `GET /api/v1/auth/accounts` — Conturile de pe ecranul de autentificare

**Cine poate apela:** fără autentificare

Lista conturilor, pentru ecranul „Cine ești?”. **Fără autentificare** și fără nicio dată medicală: doar nume,
inițiale și rol.

Frontend: afișați câte o casetă pentru fiecare cont cu `location = "ship"` pe stația de lucru de la bord și
doar contul cu `location = "earth"` pe ecranul Controlul misiunii. La click pe o casetă cereți parola acelui cont.

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
    "display_name": "Comandant",
    "initials": "CD",
    "role": "astronaut",
    "crew_id": "cm-1",
    "location": "ship"
  },
  {
    "username": "specialist2",
    "display_name": "Specialist de misiune 2",
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

#### `POST /api/v1/auth/login` — Autentificare (un cont pentru fiecare astronaut)

**Cine poate apela:** fără autentificare

**Fiecare astronaut are contul și parola lui.** Nu există cont comun de echipaj: tokenul primit e legat de un
singur `crew_id`, iar toate datele (baseline, tastare, check-in, alerte) se leagă de el.

Conturile de test sunt în README, secțiunea 1; parolele de test sunt în fișierul de seed.

* Parolă greșită → `401 invalid_credentials`. Mesajul e același și dacă utilizatorul nu există.
* 5 parole greșite pe același cont în 5 minute → `429 too_many_attempts`; contul se deblochează singur după
  60 de secunde reale. `details.retry_after_s` spune cât mai e de așteptat.
* Fiecare autentificare, reușită sau nu, se scrie în jurnalul de acces (`login` / `login_failed`).

Frontend: țineți `access_token` în memorie (nu în `localStorage`) și trimiteți-l în antetul
`Authorization: Bearer <token>`. `user.role` decide ecranul: `astronaut` → corpul interactiv,
`cmo` → coada ofițerului medical, `earth` → Controlul misiunii.

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
  "access_token": "mock-specialist2",
  "token_type": "bearer",
  "expires_in": 43200,
  "user": {
    "id": "u-cm-2",
    "username": "specialist2",
    "display_name": "Specialist de misiune 2",
    "initials": "S2",
    "role": "astronaut",
    "crew_id": "cm-2"
  }
}
```

</details>

---

#### `GET /api/v1/auth/me` — Cine sunt

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Întoarce contul din token. Util la reîncărcarea paginii și ca să afișați mereu, vizibil, cine e autentificat.

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
  "display_name": "Specialist de misiune 2",
  "initials": "S2",
  "role": "astronaut",
  "crew_id": "cm-2"
}
```

</details>

---

#### `POST /api/v1/auth/logout` — Deconectare (schimbarea astronautului)

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Invalidează tokenul curent (backend-ul trece `jti`-ul lui pe lista de tokenuri revocate). Se scrie în jurnal (`logout`).

**Schimbarea astronautului pe aceeași stație de lucru:** `logout` → ștergeți din memorie tokenul și TOATE datele
încărcate → închideți conexiunea `/events` → ecranul „Cine ești?” → `login` cu alt cont → deschideți din nou
`/events`. Colectorul de tastare se oprește la deconectare, ca apăsările să nu ajungă la alt astronaut.

În mock, tokenul rămâne valid (e textul fix `mock-<utilizator>`).

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

### 2. Misiune, mediu, ceas

#### `GET /api/v1/mission` — Starea misiunii

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Ora misiunii (SimClock), ziua curentă, mediul și starea legăturii cu Pământul.

Misiunea pornește în **ziua 96, ora 07:00** (zilele 1–95 sunt istoric generat la pornirea serverului), cu
timpul accelerat de `time_scale` ori (implicit ×60: o zi de misiune = 24 de minute reale).

Apelați-l o dată la pornire. După aceea, ora vine prin SSE (`mission.tick`), nu prin polling.

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
  "sim_now": "2027-04-15T07:42:00Z",
  "mission_day": 96,
  "total_days": 140,
  "time_scale": 60.0,
  "environment": {
    "id": "mars_transit",
    "name": "Tranzit spre Marte",
    "one_way_delay_s": 700.0,
    "gravity_g": 0.0,
    "baseline_dose_usv_h": 65.8,
    "emphasized_hazards": [
      "radiation",
      "distance",
      "… încă 1 elemente de același fel"
    ],
    "description": "Întârziere de 3–22 de minute; nivelurile 1 și 2 rezolvă aproape tot la bord."
  },
  "link": {
    "environment": "mars_transit",
    "one_way_delay_s": 700.0,
    "one_way_delay_real_s": 11.67,
    "window_open": true,
    "window_closes_at": "2027-04-15T08:24:00Z",
    "next_window_at": null,
    "queued_down": 0,
    "queued_up": 0
  }
}
```

</details>

---

#### `GET /api/v1/environments` — Lista mediilor

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Cele 4 medii pentru comutator: stație, Lună, tranzit spre Marte, bază pe Marte.

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
    "name": "Stația spațială (orbită joasă)",
    "one_way_delay_s": 1.0,
    "gravity_g": 0.0,
    "baseline_dose_usv_h": 30.5,
    "emphasized_hazards": [
      "gravity",
      "hostile_environment"
    ],
    "description": "Pământul răspunde aproape imediat; triajul trimite mai ușor la nivelul 3."
  },
  {
    "id": "moon_base",
    "name": "Bază pe Lună",
    "one_way_delay_s": 1.3,
    "gravity_g": 0.165,
    "baseline_dose_usv_h": 57.0,
    "emphasized_hazards": [
      "radiation",
      "gravity"
    ],
    "description": "Gravitație redusă, dar nu zero: alte praguri pentru oase și inimă."
  },
  "… încă 2 elemente de același fel"
]
```

</details>

---

#### `PUT /api/v1/mission/environment` — Schimbă mediul

**Cine poate apela:** astronaut, ofițer medical (cmo)

Comutatorul de mediu. Schimbă întârzierea legăturii, rata de doză de fond și pragurile dependente de gravitație.

**Efecte:** pachetele deja `in_transit` își păstrează ora de sosire; cele noi folosesc noua întârziere.
**SSE:** `environment.changed` cu noul `MissionState`.

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
  "sim_now": "2027-04-15T07:42:00Z",
  "mission_day": 96,
  "total_days": 140,
  "time_scale": 60.0,
  "environment": {
    "id": "mars_transit",
    "name": "Tranzit spre Marte",
    "one_way_delay_s": 700.0,
    "gravity_g": 0.0,
    "baseline_dose_usv_h": 65.8,
    "emphasized_hazards": [
      "radiation",
      "distance",
      "… încă 1 elemente de același fel"
    ],
    "description": "Întârziere de 3–22 de minute; nivelurile 1 și 2 rezolvă aproape tot la bord."
  },
  "link": {
    "environment": "mars_transit",
    "one_way_delay_s": 700.0,
    "one_way_delay_real_s": 11.67,
    "window_open": true,
    "window_closes_at": "2027-04-15T08:24:00Z",
    "next_window_at": null,
    "queued_down": 0,
    "queued_up": 0
  }
}
```

</details>

---

#### `PUT /api/v1/sim/clock` — Schimbă viteza sau ziua ceasului (demo)

**Cine poate apela:** astronaut, ofițer medical (cmo)

Doar pentru demo.

* `time_scale` schimbă viteza; ora curentă a misiunii rămâne aceeași.
* `mission_day` sare **înainte** la începutul acelei zile (07:00): backend-ul generează zilele lipsă cu
  simulatorul și rulează motorul peste ele, deci pot apărea alerte noi. **Înapoi nu se poate** (409
  `invalid_state`); pentru o repetiție de la capăt folosiți `POST /sim/reset`.

Derulatorul NU folosește acest endpoint: el doar citește istoricul cu `?as_of_day=`.

**SSE:** `mission.tick` cu noua zi, apoi `dashboard.changed` și eventual `alert.created`.

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
  "sim_now": "2027-04-15T07:42:00Z",
  "mission_day": 96,
  "total_days": 140,
  "time_scale": 60.0,
  "environment": {
    "id": "mars_transit",
    "name": "Tranzit spre Marte",
    "one_way_delay_s": 700.0,
    "gravity_g": 0.0,
    "baseline_dose_usv_h": 65.8,
    "emphasized_hazards": [
      "radiation",
      "distance",
      "… încă 1 elemente de același fel"
    ],
    "description": "Întârziere de 3–22 de minute; nivelurile 1 și 2 rezolvă aproape tot la bord."
  },
  "link": {
    "environment": "mars_transit",
    "one_way_delay_s": 700.0,
    "one_way_delay_real_s": 11.67,
    "window_open": true,
    "window_closes_at": "2027-04-15T08:24:00Z",
    "next_window_at": null,
    "queued_down": 0,
    "queued_up": 0
  }
}
```

</details>

---

### 3. Echipaj și corpul interactiv

#### `GET /api/v1/crew` — Lista echipajului

**Cine poate apela:** ofițer medical (cmo)

Doar pentru ofițerul medical. Conține doar starea generală, nu valori medicale.

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
      "display_name": "Comandant",
      "initials": "CD",
      "role_title": "Comandant",
      "is_cmo": false
    },
    "overall_status": "ok",
    "active_alerts": 0,
    "highest_level": null
  },
  {
    "member": {
      "id": "cm-2",
      "display_name": "Specialist de misiune 2",
      "initials": "S2",
      "role_title": "Specialist de misiune",
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

#### `GET /api/v1/crew/{crew_id}/dashboard` — Tabloul de bord al astronautului

**Cine poate apela:** astronaut, ofițer medical (cmo)

**Apelul principal al ecranului astronautului.** Într-un singur răspuns: starea celor 4 piloni (culorile zonelor
de pe corp), decalajul de percepție, semnalele încrucișate, alerta principală, seriile de zile și reamintirile.

Reîncărcați-l când primiți SSE `dashboard.changed`, `alert.created` sau `alert.updated`.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |
| `as_of_day` | query | număr întreg \| null | nu | Derulator: starea de la sfârșitul acestei zile. Fără parametru = acum. Trebuie să fie ≤ ziua curentă (zilele viitoare nu există încă) → altfel 422. (min 1) |

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
    "display_name": "Specialist de misiune 2",
    "initials": "S2",
    "role_title": "Specialist de misiune",
    "is_cmo": false
  },
  "as_of": "2027-04-15T07:42:00Z",
  "mission_day": 96,
  "overall_status": "alert",
  "pillars": [
    {
      "pillar": "behavioral",
      "name": "Tastatura",
      "body_zone": "brain",
      "status": "watch",
      "score": 71.0,
      "headline": "Tastezi cu 18% mai lent decât de obicei",
      "hazard": "isolation",
      "active_alert_id": "al-1039"
    },
    {
      "pillar": "cardio",
      "name": "Inima",
      "body_zone": "heart",
      "status": "ok",
      "score": 88.0,
      "headline": "În limitele tale din zbor",
      "hazard": "gravity",
      "active_alert_id": null
    },
    "… încă 2 elemente de același fel"
  ],
  "perception_gap": {
    "self_reported_mood": 4,
    "self_score": 80.0,
    "objective_score": 52.0,
    "gap": 28.0,
    "status": "alert",
    "explanation": "Spui că ești bine (4/5), dar tastezi cu 18% mai lent și pulsul de noapte a crescut.",
    "contributing_signals": [
      "Tastare: −18% viteză",
      "Puls de noapte: +7 bpm",
      "… încă 1 elemente de același fel"
    ]
  },
  "cross_signals": [
    {
      "id": "xs-1",
      "title": "Probabil debutul unei boli",
      "pillars": [
        "immune",
        "behavioral"
      ],
      "signals": [
        "Puls de noapte: +7 bpm",
        "Tastare: −18% viteză",
        "… încă 1 elemente de același fel"
      ],
      "confidence": 0.72,
      "explanation": "Trei semnale slabe, independente, arată în aceeași direcție."
    }
  ],
  "alerts_active_count": 2,
  "top_alert": {
    "id": "al-1042",
    "crew_id": "cm-2",
    "topic": "immune",
    "level": 2,
    "status": "alert",
    "state": "escalated",
    "title": "Puls de noapte +7 bpm, 3 nopți la rând",
    "created_at": "2027-04-14T06:10:00Z"
  },
  "streaks": [
    {
      "key": "checkin",
      "label": "Check-in zilnic",
      "days": 12,
      "best": 31
    },
    {
      "key": "split_training",
      "label": "Antrenament în două sesiuni",
      "days": 5,
      "best": 9
    },
    "… încă 1 elemente de același fel"
  ],
  "reminders": [
    {
      "id": "rm-1",
      "kind": "checkin",
      "label": "Check-in de dimineață",
      "due_at": "2027-04-15T07:00:00Z",
      "done": true,
      "overdue": false
    },
    {
      "id": "rm-2",
      "kind": "pvt",
      "label": "Test de reacție (3 minute)",
      "due_at": "2027-04-15T09:00:00Z",
      "done": false,
      "overdue": false
    },
    "… încă 1 elemente de același fel"
  ],
  "radiation_alert_active": false,
  "checkin_done_today": true
}
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/pillars/{pillar}` — Panoul unei zone a corpului

**Cine poate apela:** astronaut, ofițer medical (cmo)

Se apelează la click pe o zonă. Conține, în ordinea afișării: funcția părții corpului, pericolul spațial,
valorile față de baseline, graficul, explicația, planul de acțiune și sursele.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |
| `pillar` | cale | [Pillar](#pillar) | da |  |
| `as_of_day` | query | număr întreg \| null | nu | Derulator: starea de la sfârșitul acestei zile. Fără parametru = acum. Trebuie să fie ≤ ziua curentă (zilele viitoare nu există încă) → altfel 422. (min 1) |

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
  "name": "Santinela",
  "body_zone": "immune",
  "function_text": "Sistemul imunitar apără corpul de virusuri, bacterii și celule anormale. În zbor, stresul, somnul perturbat și radiațiile îl dereglează.",
  "hazard": "hostile_environment",
  "hazard_text": "Radiațiile și mediul închis: stresul și spațiul comun slăbesc apărarea organismului.",
  "status": "alert",
  "score": 58.0,
  "explanation": "Pulsul tău de noapte e peste normalul tău de trei nopți la rând.",
  "metrics": [
    {
      "key": "night_pulse_bpm",
      "label": "Puls de noapte",
      "value": 61.0,
      "unit": "bpm",
      "baseline": 54.0,
      "deviation_abs": 7.0,
      "deviation_pct": 13.0,
      "status": "alert",
      "source": "simulated",
      "measured_at": "2027-04-15T06:00:00Z"
    },
    {
      "key": "temperature_c",
      "label": "Temperatura",
      "value": 37.3,
      "unit": "°C",
      "baseline": 36.9,
      "deviation_abs": 0.4,
      "deviation_pct": 1.1,
      "status": "watch",
      "source": "manual",
      "measured_at": "2027-04-15T07:02:00Z"
    },
    "… încă 2 elemente de același fel"
  ],
  "chart": {
    "metric_key": "night_pulse_bpm",
    "label": "Puls de noapte",
    "unit": "bpm",
    "baseline": 54.0,
    "band_low": 51.0,
    "band_high": 57.0,
    "threshold": 58.0,
    "threshold_label": "+4 bpm, 2 nopți (NightSignal)",
    "points": [
      {
        "day": 87,
        "t": "2027-04-06T06:00:00Z",
        "value": 54.0,
        "status": "ok"
      },
      {
        "day": 88,
        "t": "2027-04-07T06:00:00Z",
        "value": 53.0,
        "status": "ok"
      },
      "… încă 8 elemente de același fel"
    ]
  },
  "plan_steps": [
    {
      "id": "st-1",
      "text": "Culcă-te cu o oră mai devreme în următoarele 3 nopți.",
      "done": true,
      "done_at": "2027-04-14T21:30:00Z"
    },
    {
      "id": "st-2",
      "text": "Măsoară temperatura dimineața și seara.",
      "done": false,
      "done_at": null
    },
    "… încă 1 elemente de același fel"
  ],
  "active_alert_id": "al-1042",
  "recheck_at": "2027-04-17T07:00:00Z",
  "sources": [
    {
      "citation": "Alavi et al. (2022), Real-time alerting system for COVID-19 and other stress events using wearable data, Nature Medicine 28:175–184",
      "url": "https://www.nature.com/articles/s41591-021-01593-2",
      "verification": "verified",
      "derivation": "published",
      "evidence_strength": "moderată"
    },
    {
      "citation": "Rooney et al. (2019), Herpes Virus Reactivation in Astronauts During Spaceflight, Frontiers in Microbiology 10:16",
      "url": "https://www.frontiersin.org/articles/10.3389/fmicb.2019.00016/full",
      "verification": "verified",
      "derivation": "published",
      "evidence_strength": "moderată"
    },
    "… încă 1 elemente de același fel"
  ],
  "limits_text": "Algoritmul nu distinge tipul de infecție și poate da alarme false. A fost validat pe civili, nu pe astronauți.",
  "data_is_simulated": true
}
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/pillars/{pillar}/series` — Seria unei metrici (grafic)

**Cine poate apela:** astronaut, ofițer medical (cmo)

Pentru un al doilea grafic sau pentru un interval mai lung decât cel din panou (care are ultimele 10 zile).

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |
| `pillar` | cale | [Pillar](#pillar) | da |  |
| `metric` | query | text | da | Cheia metricii, ex. `night_pulse_bpm`. Vezi README, „Chei de metrici”. |
| `from_day` | query | număr întreg | nu |  Implicit: `1`. (min 1) |
| `to_day` | query | număr întreg \| null | nu | Implicit: ziua curentă. (min 1) |

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
  "label": "Puls de noapte",
  "unit": "bpm",
  "baseline": 54.0,
  "band_low": 51.0,
  "band_high": 57.0,
  "threshold": 58.0,
  "threshold_label": "+4 bpm, 2 nopți (NightSignal)",
  "points": [
    {
      "day": 87,
      "t": "2027-04-06T06:00:00Z",
      "value": 54.0,
      "status": "ok"
    },
    {
      "day": 88,
      "t": "2027-04-07T06:00:00Z",
      "value": 53.0,
      "status": "ok"
    },
    "… încă 8 elemente de același fel"
  ]
}
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/timeline` — Istoric pe zile (derulator)

**Cine poate apela:** astronaut, ofițer medical (cmo)

Starea fiecărui pilon pe fiecare zi **care a avut loc**: de la `from_day` până la ziua curentă (misiunea
pornește în ziua 96, deci la început sunt 96 de zile). Zilele viitoare nu apar; bara derulatorului arată restul
până la `total_days` (din `/mission`) ca „încă nu”.

Se încarcă o dată la pornire și se reîncarcă la `mission.tick` doar când se schimbă `mission_day`.
Când utilizatorul se oprește pe o zi, reîncărcați `dashboard` și panoul deschis cu `?as_of_day=`.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |
| `from_day` | query | număr întreg | nu |  Implicit: `1`. (min 1) |
| `to_day` | query | număr întreg \| null | nu | Implicit și maximum: ziua curentă. (min 1) |

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
      "overall_status": "alert",
      "pillars": {
        "behavioral": "ok",
        "cardio": "ok",
        "immune": "alert",
        "musculoskeletal": "ok"
      },
      "events": []
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
      "events": []
    },
    "… încă 1 elemente de același fel"
  ]
}
```

</details>

---

### 4. Check-in

#### `GET /api/v1/checkin/schema` — Câmpurile check-in-ului

**Cine poate apela:** astronaut, ofițer medical (cmo)

Lista câmpurilor, cu textele „Cum se măsoară”, „Ce înseamnă” și „De ce contează în spațiu” și cu limitele de
plauzibilitate (`min`/`max`). Frontend-ul construiește formularul din acest răspuns; nu țineți textele în cod.

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
      "label": "Starea de spirit",
      "unit": "",
      "input": "scale_1_5",
      "min": 1.0,
      "max": 5.0,
      "step": 1.0,
      "choices": null,
      "required": true,
      "how_to_measure": "Alege de la 1 (foarte rău) la 5 (foarte bine).",
      "what_it_means": "Cum te simți tu; intră în decalajul de percepție.",
      "why_in_space": "Izolarea și distanța față de Pământ apasă pe sănătatea comportamentală.",
      "pillar": "behavioral",
      "source": null
    },
    {
      "key": "systolic_mmhg",
      "label": "Tensiunea (sistolică)",
      "unit": "mmHg",
      "input": "number",
      "min": 60.0,
      "max": 250.0,
      "step": 1.0,
      "choices": null,
      "required": false,
      "how_to_measure": "Cu manșeta, în repaus, după câteva minute de stat jos.",
      "what_it_means": "Presiunea sângelui pe artere; o urmărim ca tendință față de normalul tău.",
      "why_in_space": "În microgravitație fluidele se mută spre cap, iar tensiunea scade de obicei față de Pământ.",
      "pillar": "cardio",
      "source": {
        "citation": "NASA HRP — Risk of Cardiovascular Adaptations",
        "url": "https://www.nasa.gov/reference/risk-of-cardiovascular-adaptations/",
        "verification": "unverified",
        "derivation": "derived",
        "evidence_strength": "slabă"
      }
    },
    "… încă 6 elemente de același fel"
  ]
}
```

</details>

---

#### `POST /api/v1/crew/{crew_id}/checkins` — Trimite check-in-ul de dimineață

**Cine poate apela:** astronaut, ofițer medical (cmo)

Salvează check-in-ul zilei. **Un singur check-in pe zi de misiune**: al doilea îl înlocuiește pe primul.

Ce face backend-ul, în ordine:
1. validează fiecare câmp față de `min`/`max` din schemă; câmpurile imposibile NU dau eroare 422, ci apar în
   `rejected` și se salvează ca `null` (restul check-in-ului rămâne valid);
2. compară valorile cu baseline-ul personal;
3. recalculează decalajul de percepție;
4. rulează triajul și creează alerte, dacă e cazul;
5. actualizează seria de zile.

**SSE:** `dashboard.changed`, plus `alert.created` pentru fiecare alertă nouă.

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
    "id": "ck-0096",
    "crew_id": "cm-2",
    "mission_day": 96,
    "created_at": "2027-04-15T07:42:00Z",
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
      "message": "Temperatura: 41.9 °C e în afara intervalului posibil (34.0–41.5). Măsoară din nou."
    }
  ],
  "perception_gap": {
    "self_reported_mood": 4,
    "self_score": 80.0,
    "objective_score": 52.0,
    "gap": 28.0,
    "status": "alert",
    "explanation": "Spui că ești bine (4/5), dar tastezi cu 18% mai lent și pulsul de noapte a crescut.",
    "contributing_signals": [
      "Tastare: −18% viteză",
      "Puls de noapte: +7 bpm",
      "… încă 1 elemente de același fel"
    ]
  },
  "alerts_created": [],
  "streak": {
    "key": "checkin",
    "label": "Check-in zilnic",
    "days": 12,
    "best": 31
  },
  "message": "Check-in salvat. 12 zile la rând."
}
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/checkins` — Istoricul check-in-urilor

**Cine poate apela:** astronaut, ofițer medical (cmo)

Check-in-urile din interval, cele mai noi primele.

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
    "id": "ck-0096",
    "crew_id": "cm-2",
    "mission_day": 96,
    "created_at": "2027-04-15T07:02:00Z",
    "values": {
      "mood": 4,
      "systolic_mmhg": 112.0,
      "diastolic_mmhg": 72.0,
      "pulse_bpm": 58.0,
      "glucose_mg_dl": 92.0,
      "temperature_c": 37.3,
      "sleep_hours": 5.5,
      "meals_eaten": "some",
      "note": null
    }
  }
]
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/checkins/today` — Check-in-ul de azi

**Cine poate apela:** astronaut, ofițer medical (cmo)

Întoarce check-in-ul zilei curente sau `null` dacă nu a fost făcut. Folosiți-l ca să decideți dacă afișați formularul.

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
  "id": "ck-0096",
  "crew_id": "cm-2",
  "mission_day": 96,
  "created_at": "2027-04-15T07:02:00Z",
  "values": {
    "mood": 4,
    "systolic_mmhg": 112.0,
    "diastolic_mmhg": 72.0,
    "pulse_bpm": 58.0,
    "glucose_mg_dl": 92.0,
    "temperature_c": 37.3,
    "sleep_hours": 5.5,
    "meals_eaten": "some",
    "note": null
  }
}
```

</details>

---

### 5. Tastare și test de reacție

#### `POST /api/v1/crew/{crew_id}/keystrokes/batches` — Trimite un lot de apăsări de taste

**Cine poate apela:** astronaut, ofițer medical (cmo)

**Confidențialitate: trimiteți doar timpii și clasa tastei, niciodată caracterul.** Backend-ul respinge cu 422
orice câmp în plus (ex. `key`, `code`, `text`).

Frontend: adunați evenimentele `keydown`/`keyup` și trimiteți un lot la ~5 secunde sau la 200 de taste, cu
același `session_id` cât timp utilizatorul scrie în același câmp. Răspunsul conține trăsăturile cumulate ale
sesiunii, deci îl puteți afișa direct în barele live.

Primele sesiuni construiesc baseline-ul: cât timp `baseline_ready` e `false`, `status` e `unknown`.

**SSE:** `alert.created` dacă abaterea trece pragul.

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
    "hold_ms_mean": 112.0,
    "hold_ms_sd": 27.8,
    "flight_ms_mean": 221.5,
    "flight_ms_sd": 88.0,
    "backspace_rate": 0.07,
    "keys_per_min": 176.0,
    "n_keys": 3
  },
  "baseline": {
    "hold_ms_mean": 96.4,
    "hold_ms_sd": 21.3,
    "flight_ms_mean": 182.0,
    "flight_ms_sd": 64.9,
    "backspace_rate": 0.06,
    "keys_per_min": 214.0,
    "n_keys": 5200
  },
  "deviation_z": {
    "hold_ms_mean": 1.9,
    "flight_ms_mean": 1.5,
    "keys_per_min": -1.6,
    "backspace_rate": 0.3
  },
  "fatigue_index": 68.0,
  "status": "watch",
  "baseline_ready": true,
  "baseline_sessions": 9
}
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/keystrokes/summary` — Rezumatul tastării

**Cine poate apela:** astronaut, ofițer medical (cmo)

Baseline-ul personal, ultima sesiune și sesiunile recente. Pentru cardul „Ritmul tău” și pentru comparația din demo.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |
| `last` | query | număr întreg | nu | Câte sesiuni recente să întoarcă. Implicit: `10`. (min 1; max 100) |

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
    "hold_ms_mean": 96.4,
    "hold_ms_sd": 21.3,
    "flight_ms_mean": 182.0,
    "flight_ms_sd": 64.9,
    "backspace_rate": 0.06,
    "keys_per_min": 214.0,
    "n_keys": 5200
  },
  "current": {
    "hold_ms_mean": 112.0,
    "hold_ms_sd": 27.8,
    "flight_ms_mean": 221.5,
    "flight_ms_sd": 88.0,
    "backspace_rate": 0.07,
    "keys_per_min": 176.0,
    "n_keys": 380
  },
  "fatigue_index": 68.0,
  "status": "watch",
  "baseline_ready": true,
  "sessions": [
    {
      "session_id": "s-0",
      "at": "2027-04-10T07:15:00Z",
      "keys_per_min": 213.0,
      "hold_ms_mean": 97.0,
      "fatigue_index": 6.0,
      "status": "ok"
    },
    {
      "session_id": "s-1",
      "at": "2027-04-11T07:15:00Z",
      "keys_per_min": 205.0,
      "hold_ms_mean": 99.0,
      "fatigue_index": 18.0,
      "status": "ok"
    },
    "… încă 4 elemente de același fel"
  ]
}
```

</details>

---

#### `POST /api/v1/crew/{crew_id}/pvt` — Trimite un test de reacție (PVT-B)

**Cine poate apela:** astronaut, ofițer medical (cmo)

Testul de 3 minute rulează integral în frontend; aici trimiteți toate încercările la sfârșit.

Backend-ul calculează media 1/RT, lapsusurile (RT ≥ 355 ms) și abaterea față de baseline. Primele 2–3 teste
sunt de antrenament și nu intră în baseline.

**SSE:** `dashboard.changed`.

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
  "id": "pvt-0031",
  "crew_id": "cm-2",
  "at": "2027-04-14T09:05:00Z",
  "n_trials": 48,
  "mean_rt_ms": 312.5,
  "mean_speed": 3.31,
  "lapses": 6,
  "false_starts": 1,
  "baseline_speed": 3.72,
  "deviation_sd": -1.4,
  "status": "watch"
}
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/pvt` — Istoricul testelor de reacție

**Cine poate apela:** astronaut, ofițer medical (cmo)

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
    "id": "pvt-0031",
    "crew_id": "cm-2",
    "at": "2027-04-14T09:05:00Z",
    "n_trials": 48,
    "mean_rt_ms": 312.5,
    "mean_speed": 3.31,
    "lapses": 6,
    "false_starts": 1,
    "baseline_speed": 3.72,
    "deviation_sd": -1.4,
    "status": "watch"
  }
]
```

</details>

---

### 6. Exerciții

#### `GET /api/v1/crew/{crew_id}/exercise/today` — Planul de exerciții de azi

**Cine poate apela:** astronaut, ofițer medical (cmo)

Sesiunile planificate și făcute, scorul de încărcare, recomandarea de împărțire în două sesiuni și seria de zile.

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
  "completed_sessions": 1,
  "loading_score": 38.0,
  "loading_target": 80.0,
  "split_recommended": true,
  "recommendation_text": "Împarte antrenamentul de azi în două sesiuni, la câteva ore distanță.",
  "streak": {
    "key": "split_training",
    "label": "Antrenament în două sesiuni",
    "days": 5,
    "best": 9
  },
  "sessions": [
    {
      "kind": "resistance",
      "started_at": "2027-04-15T08:30:00Z",
      "duration_min": 40.0,
      "sets": [
        {
          "exercise": "genuflexiuni ARED",
          "reps": 10,
          "load_kg": 85.0
        },
        {
          "exercise": "îndreptări ARED",
          "reps": 8,
          "load_kg": 95.0
        }
      ],
      "id": "ex-0211",
      "crew_id": "cm-2",
      "mission_day": 96,
      "loading_score": 38.0,
      "source": "simulated"
    }
  ],
  "projection": {
    "current_plan_pct_month": -0.64,
    "split_plan_pct_month": -0.45,
    "note": "Estimare. Efectul împărțirii e demonstrat doar pe animale (Robling 2002)."
  }
}
```

</details>

---

#### `POST /api/v1/crew/{crew_id}/exercise/sessions` — Înregistrează o sesiune de exerciții

**Cine poate apela:** astronaut, ofițer medical (cmo)

În versiunea reală, jurnalul vine de la aparat. În prototip îl trimite simulatorul sau astronautul, de mână.

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
  "id": "ex-0212",
  "crew_id": "cm-2",
  "mission_day": 96,
  "loading_score": 41.0,
  "source": "manual"
}
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/exercise/sessions` — Istoricul sesiunilor

**Cine poate apela:** astronaut, ofițer medical (cmo)

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
    "started_at": "2027-04-15T08:30:00Z",
    "duration_min": 40.0,
    "sets": [
      {
        "exercise": "genuflexiuni ARED",
        "reps": 10,
        "load_kg": 85.0
      },
      {
        "exercise": "îndreptări ARED",
        "reps": 8,
        "load_kg": 95.0
      }
    ],
    "id": "ex-0211",
    "crew_id": "cm-2",
    "mission_day": 96,
    "loading_score": 38.0,
    "source": "simulated"
  }
]
```

</details>

---

### 7. Alerte, triaj, catalog

#### `GET /api/v1/crew/{crew_id}/alerts` — Alertele unui membru al echipajului

**Cine poate apela:** astronaut, ofițer medical (cmo)

Lista scurtă, cele mai grave primele. Ofițerul medical primește aici doar alertele de nivel ≥ 2 ale altor membri.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | cale | text | da |  |
| `state` | query | [AlertState](#alertstate) \| null | nu | Filtru. Fără parametru = toate cele nerezolvate. |
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
    "id": "al-1042",
    "crew_id": "cm-2",
    "topic": "immune",
    "level": 2,
    "status": "alert",
    "state": "escalated",
    "title": "Puls de noapte +7 bpm, 3 nopți la rând",
    "created_at": "2027-04-14T06:10:00Z"
  },
  {
    "id": "al-1039",
    "crew_id": "cm-2",
    "topic": "behavioral",
    "level": 1,
    "status": "watch",
    "state": "active",
    "title": "Tastezi cu 18% mai lent decât de obicei",
    "created_at": "2027-04-15T07:20:00Z"
  }
]
```

</details>

---

#### `GET /api/v1/cmo/queue` — Coada ofițerului medical

**Cine poate apela:** ofițer medical (cmo)

Toate alertele de nivel 2 și 3 nerezolvate, din tot echipajul. Ecranul principal al rolului `cmo`.

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
    "id": "al-1042",
    "crew_id": "cm-2",
    "topic": "immune",
    "level": 2,
    "status": "alert",
    "state": "escalated",
    "title": "Puls de noapte +7 bpm, 3 nopți la rând",
    "created_at": "2027-04-14T06:10:00Z"
  }
]
```

</details>

---

#### `GET /api/v1/alerts/{alert_id}` — Alerta completă

**Cine poate apela:** astronaut, ofițer medical (cmo)

Dovezile, cauza (individuală sau de mediu), recomandarea din catalog cu sursa ei, planul de acțiune, data
reverificării și istoricul. Fiecare citire de către ofițerul medical se scrie în jurnalul de acces.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `alert_id` | cale | text | da |  |

**Răspuns 200:** [Alert](#alert)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/alerts/al-1042
```

Răspuns `200`:

```json
{
  "id": "al-1042",
  "crew_id": "cm-2",
  "topic": "immune",
  "level": 2,
  "status": "alert",
  "state": "escalated",
  "title": "Puls de noapte +7 bpm, 3 nopți la rând",
  "created_at": "2027-04-14T06:10:00Z",
  "explanation": "Pulsul tău de noapte e cu 7 bpm peste normalul tău de trei nopți. Asta apare des cu 2–3 zile înaintea unei infecții.",
  "cause": "individual",
  "cause_explanation": "Doar tu ai această abatere; ceilalți membri ai echipajului sunt în limite.",
  "evidence": [
    {
      "metric_key": "night_pulse_bpm",
      "label": "Puls de noapte",
      "value": 61.0,
      "unit": "bpm",
      "baseline": 54.0,
      "deviation_text": "+7 bpm peste mediana personală, 3 nopți"
    },
    {
      "metric_key": "temperature_c",
      "label": "Temperatura",
      "value": 37.3,
      "unit": "°C",
      "baseline": 36.9,
      "deviation_text": "+0,4 °C față de normalul tău"
    },
    "… încă 1 elemente de același fel"
  ],
  "recommendation": {
    "id": "immune-2-1",
    "topic": "immune",
    "level": 2,
    "trigger": "Alertă roșie NightSignal: puls mediu de noapte ≥ +4 bpm peste mediana personală două nopți la rând, mai ales dacă temperatura pielii depășește pragul SHADOW derivat sau apar simptome.",
    "action": "Anunță ofițerul medical de la bord (CMO) cu graficul puls/temperatură vs baseline și jurnalul de simptome. Doar CMO decide evaluarea sau tratamentul simptomatic din farmacia ISS (antihistaminice, antiinflamatoare, antimicrobiene); aplicația nu recomandă medicamente.",
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
      "text": "Culcă-te cu o oră mai devreme în următoarele 3 nopți.",
      "done": true,
      "done_at": "2027-04-14T21:30:00Z"
    },
    {
      "id": "st-2",
      "text": "Măsoară temperatura dimineața și seara.",
      "done": false,
      "done_at": null
    },
    "… încă 1 elemente de același fel"
  ],
  "recheck_at": "2027-04-17T07:00:00Z",
  "packet_id": "pk-0007",
  "earth_reply": null,
  "history": [
    {
      "at": "2027-04-14T06:10:00Z",
      "actor": "SHADOW",
      "role": null,
      "action": "created",
      "note": null
    },
    {
      "at": "2027-04-14T07:05:00Z",
      "actor": "Specialist de misiune 2",
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

#### `POST /api/v1/alerts/{alert_id}/ack` — Confirmă că ai văzut alerta

**Cine poate apela:** astronaut, ofițer medical (cmo)

Trece alerta din `active` în `acknowledged`. Nu se poate apela pe o alertă deja escaladată sau rezolvată (409 `invalid_state`).

**SSE:** `alert.updated`.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `alert_id` | cale | text | da |  |

**Răspuns 200:** [Alert](#alert)

**Erori posibile:** 401, 403, 404, 422, 409 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
POST /api/v1/alerts/al-1039/ack
```

Răspuns `200`:

```json
{
  "id": "al-1039",
  "crew_id": "cm-2",
  "topic": "behavioral",
  "level": 1,
  "status": "watch",
  "state": "acknowledged",
  "title": "Tastezi cu 18% mai lent decât de obicei",
  "created_at": "2027-04-15T07:20:00Z",
  "explanation": "Ritmul tău de tastare s-a abătut de la normalul tău, deși la check-in ai spus că te simți bine.",
  "cause": "individual",
  "cause_explanation": "Abaterea apare doar la tine.",
  "evidence": [
    {
      "metric_key": "keys_per_min",
      "label": "Viteză de tastare",
      "value": 176.0,
      "unit": "taste/min",
      "baseline": 214.0,
      "deviation_text": "−18%"
    }
  ],
  "recommendation": {
    "id": "behavioral-1-1",
    "topic": "behavioral",
    "level": 1,
    "trigger": "PVT-B sau tastarea arată abatere față de baseline-ul personal (ex. 1/RT sub prag), chiar dacă astronautul se simte odihnit",
    "action": "Nu te baza pe senzația subiectivă: refă PVT-B-ul de 3 minute înaintea oricărei sarcini critice și amân-o, dacă se poate, până la normalizare.",
    "hrp_risk": "Risk of Performance Decrements and Adverse Health Outcomes Resulting from Sleep Loss, Circadian Desynchronization, and Work Overload",
    "hrp_risk_url": "https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=100",
    "source": {
      "citation": "Van Dongen HPA, Maislin G, Mullington JM, Dinges DF. (2003). The cumulative cost of additional wakefulness: dose-response effects on neurobehavioral functions and sleep physiology from chronic sleep restriction and total sleep deprivation. Sleep 26(2):117-126. Erratum: Sleep 2004;27(4):600. + Evidence Report NASA 2016 (secțiunea Chronic Sleep Loss)",
      "url": "https://pubmed.ncbi.nlm.nih.gov/12683469/",
      "verification": "verified",
      "derivation": "published",
      "evidence_strength": null
    }
  },
  "plan_steps": [
    {
      "id": "st-1",
      "text": "Fă testul de reacție de 3 minute.",
      "done": false,
      "done_at": null
    },
    {
      "id": "st-2",
      "text": "Amână sarcinile critice cu 2 ore, dacă se poate.",
      "done": false,
      "done_at": null
    }
  ],
  "recheck_at": "2027-04-16T07:00:00Z",
  "packet_id": null,
  "earth_reply": null,
  "history": [
    {
      "at": "2027-04-15T07:20:00Z",
      "actor": "SHADOW",
      "role": null,
      "action": "created",
      "note": null
    },
    {
      "at": "2027-04-15T07:42:00Z",
      "actor": "Specialist de misiune 2",
      "role": "astronaut",
      "action": "acknowledged",
      "note": null
    }
  ]
}
```

</details>

---

#### `PUT /api/v1/alerts/{alert_id}/plan/steps/{step_id}` — Bifează un pas din plan

**Cine poate apela:** astronaut, ofițer medical (cmo)

Bifează sau debifează un pas al planului de acțiune.

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
PUT /api/v1/alerts/al-1042/plan/steps/st-2
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
  "id": "al-1042",
  "crew_id": "cm-2",
  "topic": "immune",
  "level": 2,
  "status": "alert",
  "state": "escalated",
  "title": "Puls de noapte +7 bpm, 3 nopți la rând",
  "created_at": "2027-04-14T06:10:00Z",
  "explanation": "Pulsul tău de noapte e cu 7 bpm peste normalul tău de trei nopți. Asta apare des cu 2–3 zile înaintea unei infecții.",
  "cause": "individual",
  "cause_explanation": "Doar tu ai această abatere; ceilalți membri ai echipajului sunt în limite.",
  "evidence": [
    {
      "metric_key": "night_pulse_bpm",
      "label": "Puls de noapte",
      "value": 61.0,
      "unit": "bpm",
      "baseline": 54.0,
      "deviation_text": "+7 bpm peste mediana personală, 3 nopți"
    },
    {
      "metric_key": "temperature_c",
      "label": "Temperatura",
      "value": 37.3,
      "unit": "°C",
      "baseline": 36.9,
      "deviation_text": "+0,4 °C față de normalul tău"
    },
    "… încă 1 elemente de același fel"
  ],
  "recommendation": {
    "id": "immune-2-1",
    "topic": "immune",
    "level": 2,
    "trigger": "Alertă roșie NightSignal: puls mediu de noapte ≥ +4 bpm peste mediana personală două nopți la rând, mai ales dacă temperatura pielii depășește pragul SHADOW derivat sau apar simptome.",
    "action": "Anunță ofițerul medical de la bord (CMO) cu graficul puls/temperatură vs baseline și jurnalul de simptome. Doar CMO decide evaluarea sau tratamentul simptomatic din farmacia ISS (antihistaminice, antiinflamatoare, antimicrobiene); aplicația nu recomandă medicamente.",
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
      "text": "Culcă-te cu o oră mai devreme în următoarele 3 nopți.",
      "done": true,
      "done_at": "2027-04-14T21:30:00Z"
    },
    {
      "id": "st-2",
      "text": "Măsoară temperatura dimineața și seara.",
      "done": true,
      "done_at": "2027-04-15T07:42:00Z"
    },
    "… încă 1 elemente de același fel"
  ],
  "recheck_at": "2027-04-17T07:00:00Z",
  "packet_id": "pk-0007",
  "earth_reply": null,
  "history": [
    {
      "at": "2027-04-14T06:10:00Z",
      "actor": "SHADOW",
      "role": null,
      "action": "created",
      "note": null
    },
    {
      "at": "2027-04-14T07:05:00Z",
      "actor": "Specialist de misiune 2",
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

#### `POST /api/v1/alerts/{alert_id}/escalate` — Escaladează alerta

**Cine poate apela:** astronaut, ofițer medical (cmo)

Urcă alerta un nivel.

* `to_level = 2` — astronautul o trimite ofițerului medical. Apare în `/cmo/queue`.
* `to_level = 3` — **doar rolul `cmo`**. Backend-ul creează automat un pachet semnat și criptat în coada spre
  Pământ și pune id-ul lui în `packet_id`. Nu mai trebuie apelat `/link/outbox`.

Nivelul nu poate coborî (409 `invalid_state`). Alertele critice pot fi escaladate și automat de motorul de triaj.

**SSE:** `alert.updated`, iar la nivelul 3 și `packet.sent` când se deschide fereastra.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `alert_id` | cale | text | da |  |

**Corpul cererii:** [EscalateRequest](#escalaterequest)

**Răspuns 200:** [Alert](#alert)

**Erori posibile:** 401, 403, 404, 422, 409 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>medic</code>)</summary>

```http
POST /api/v1/alerts/al-1042/escalate
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
  "id": "al-1042",
  "crew_id": "cm-2",
  "topic": "immune",
  "level": 3,
  "status": "alert",
  "state": "escalated",
  "title": "Puls de noapte +7 bpm, 3 nopți la rând",
  "created_at": "2027-04-14T06:10:00Z",
  "explanation": "Pulsul tău de noapte e cu 7 bpm peste normalul tău de trei nopți. Asta apare des cu 2–3 zile înaintea unei infecții.",
  "cause": "individual",
  "cause_explanation": "Doar tu ai această abatere; ceilalți membri ai echipajului sunt în limite.",
  "evidence": [
    {
      "metric_key": "night_pulse_bpm",
      "label": "Puls de noapte",
      "value": 61.0,
      "unit": "bpm",
      "baseline": 54.0,
      "deviation_text": "+7 bpm peste mediana personală, 3 nopți"
    },
    {
      "metric_key": "temperature_c",
      "label": "Temperatura",
      "value": 37.3,
      "unit": "°C",
      "baseline": 36.9,
      "deviation_text": "+0,4 °C față de normalul tău"
    },
    "… încă 1 elemente de același fel"
  ],
  "recommendation": {
    "id": "immune-2-1",
    "topic": "immune",
    "level": 2,
    "trigger": "Alertă roșie NightSignal: puls mediu de noapte ≥ +4 bpm peste mediana personală două nopți la rând, mai ales dacă temperatura pielii depășește pragul SHADOW derivat sau apar simptome.",
    "action": "Anunță ofițerul medical de la bord (CMO) cu graficul puls/temperatură vs baseline și jurnalul de simptome. Doar CMO decide evaluarea sau tratamentul simptomatic din farmacia ISS (antihistaminice, antiinflamatoare, antimicrobiene); aplicația nu recomandă medicamente.",
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
      "text": "Culcă-te cu o oră mai devreme în următoarele 3 nopți.",
      "done": true,
      "done_at": "2027-04-14T21:30:00Z"
    },
    {
      "id": "st-2",
      "text": "Măsoară temperatura dimineața și seara.",
      "done": true,
      "done_at": "2027-04-15T07:42:00Z"
    },
    "… încă 1 elemente de același fel"
  ],
  "recheck_at": "2027-04-17T07:00:00Z",
  "packet_id": "pk-0007",
  "earth_reply": null,
  "history": [
    {
      "at": "2027-04-14T06:10:00Z",
      "actor": "SHADOW",
      "role": null,
      "action": "created",
      "note": null
    },
    {
      "at": "2027-04-14T07:05:00Z",
      "actor": "Specialist de misiune 2",
      "role": "astronaut",
      "action": "acknowledged",
      "note": null
    },
    "… încă 2 elemente de același fel"
  ]
}
```

</details>

---

#### `POST /api/v1/alerts/{alert_id}/resolve` — Închide alerta

**Cine poate apela:** astronaut, ofițer medical (cmo)

Astronautul poate închide alertele de nivel 1; cele de nivel 2 și 3 le închide ofițerul medical.
`outcome = monitoring` păstrează alerta deschisă și mută `recheck_at` cu încă o zi.

**SSE:** `alert.updated`.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `alert_id` | cale | text | da |  |

**Corpul cererii:** [ResolveRequest](#resolverequest)

**Răspuns 200:** [Alert](#alert)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
POST /api/v1/alerts/al-1039/resolve
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
  "id": "al-1039",
  "crew_id": "cm-2",
  "topic": "behavioral",
  "level": 1,
  "status": "watch",
  "state": "resolved",
  "title": "Tastezi cu 18% mai lent decât de obicei",
  "created_at": "2027-04-15T07:20:00Z",
  "explanation": "Ritmul tău de tastare s-a abătut de la normalul tău, deși la check-in ai spus că te simți bine.",
  "cause": "individual",
  "cause_explanation": "Abaterea apare doar la tine.",
  "evidence": [
    {
      "metric_key": "keys_per_min",
      "label": "Viteză de tastare",
      "value": 176.0,
      "unit": "taste/min",
      "baseline": 214.0,
      "deviation_text": "−18%"
    }
  ],
  "recommendation": {
    "id": "behavioral-1-1",
    "topic": "behavioral",
    "level": 1,
    "trigger": "PVT-B sau tastarea arată abatere față de baseline-ul personal (ex. 1/RT sub prag), chiar dacă astronautul se simte odihnit",
    "action": "Nu te baza pe senzația subiectivă: refă PVT-B-ul de 3 minute înaintea oricărei sarcini critice și amân-o, dacă se poate, până la normalizare.",
    "hrp_risk": "Risk of Performance Decrements and Adverse Health Outcomes Resulting from Sleep Loss, Circadian Desynchronization, and Work Overload",
    "hrp_risk_url": "https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=100",
    "source": {
      "citation": "Van Dongen HPA, Maislin G, Mullington JM, Dinges DF. (2003). The cumulative cost of additional wakefulness: dose-response effects on neurobehavioral functions and sleep physiology from chronic sleep restriction and total sleep deprivation. Sleep 26(2):117-126. Erratum: Sleep 2004;27(4):600. + Evidence Report NASA 2016 (secțiunea Chronic Sleep Loss)",
      "url": "https://pubmed.ncbi.nlm.nih.gov/12683469/",
      "verification": "verified",
      "derivation": "published",
      "evidence_strength": null
    }
  },
  "plan_steps": [
    {
      "id": "st-1",
      "text": "Fă testul de reacție de 3 minute.",
      "done": false,
      "done_at": null
    },
    {
      "id": "st-2",
      "text": "Amână sarcinile critice cu 2 ore, dacă se poate.",
      "done": false,
      "done_at": null
    }
  ],
  "recheck_at": "2027-04-16T07:00:00Z",
  "packet_id": null,
  "earth_reply": null,
  "history": [
    {
      "at": "2027-04-15T07:20:00Z",
      "actor": "SHADOW",
      "role": null,
      "action": "created",
      "note": null
    },
    {
      "at": "2027-04-15T07:42:00Z",
      "actor": "Specialist de misiune 2",
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

#### `GET /api/v1/catalog/recommendations` — Catalogul de recomandări

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Recomandările scrise de echipă pe baza riscurilor NASA HRP, fiecare cu sursa ei. Medicul AI doar le reformulează.

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
    "trigger": "Alertă galbenă: pulsul mediu de noapte e cu +3 bpm peste mediana personală, sau o singură noapte cu ≥ +4 bpm (prag din NightSignal; folosirea lui ca nivel 1 e o alegere SHADOW).",
    "action": "Completează în aplicație jurnalul scurt de context: simptome (tuse, febră, durere de cap, oboseală), somn scurt, stres, efort intens. Remăsoară noaptea următoare. În studiu, alertele au fost declanșate și de stres sau alte evenimente fără legătură cu o infecție, iar participanții au adnotat alertele prin chestionare.",
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
    "trigger": "Orice alertă imună activă sau somn sub baseline-ul personal.",
    "action": "Prioritizează somnul și managementul oboselii conform programului (somnul și ritmul circadian sunt legate direct de funcția imună; pe orbită somnul e redus și ritmurile sunt dezaliniate). Folosește serviciile de suport comportamental/oboseală disponibile.",
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

#### `GET /api/v1/catalog/recommendations/{rec_id}` — O recomandare din catalog

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
  "trigger": "Alertă roșie NightSignal: puls mediu de noapte ≥ +4 bpm peste mediana personală două nopți la rând, mai ales dacă temperatura pielii depășește pragul SHADOW derivat sau apar simptome.",
  "action": "Anunță ofițerul medical de la bord (CMO) cu graficul puls/temperatură vs baseline și jurnalul de simptome. Doar CMO decide evaluarea sau tratamentul simptomatic din farmacia ISS (antihistaminice, antiinflamatoare, antimicrobiene); aplicația nu recomandă medicamente.",
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

### 8. Legătura cu Pământul

#### `GET /api/v1/link/status` — Starea legăturii

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Întârzierea curentă, dacă fereastra e deschisă și câte pachete așteaptă în fiecare sens.

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
  "window_closes_at": "2027-04-15T08:24:00Z",
  "next_window_at": null,
  "queued_down": 0,
  "queued_up": 0
}
```

</details>

---

#### `GET /api/v1/link/packets` — Coada de pachete

**Cine poate apela:** ofițer medical (cmo), Pământ (earth)

Plicurile pachetelor, cele mai noi primele — tabelul din ecranul „Controlul misiunii”.

Câmpul `progress` e calculat la momentul răspunsului. Pentru o bară fluidă, animați local folosind
`eta_real_s` și reîncărcați lista doar la SSE `packet.sent` / `packet.arrived` / `packet.rejected`.

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
    "id": "pk-0007",
    "seq": 7,
    "direction": "down",
    "kind": "alert_l3",
    "status": "in_transit",
    "title": "Imunitar · puls de noapte +7 bpm, 3 nopți",
    "sender": "Ofițer medical de bord",
    "level": 3,
    "alert_status": "alert",
    "crew_id": "cm-2",
    "alert_id": "al-1042",
    "in_reply_to": null,
    "created_at": "2027-04-15T07:30:00Z",
    "sent_at": "2027-04-15T07:35:00Z",
    "arrives_at": "2027-04-15T07:46:40Z",
    "delivered_at": null,
    "progress": 0.64,
    "eta_real_s": 4.2,
    "signature_valid": null,
    "reject_reason": null,
    "size_bytes": 1840
  },
  {
    "id": "pk-0006",
    "seq": 6,
    "direction": "down",
    "kind": "weekly_summary",
    "status": "delivered",
    "title": "Rezumat săptămânal aprobat de astronaut",
    "sender": "Specialist de misiune 2",
    "level": null,
    "alert_status": null,
    "crew_id": "cm-2",
    "alert_id": null,
    "in_reply_to": null,
    "created_at": "2027-04-14T09:20:00Z",
    "sent_at": "2027-04-14T09:29:00Z",
    "arrives_at": "2027-04-14T09:41:00Z",
    "delivered_at": "2027-04-14T09:41:00Z",
    "progress": 1.0,
    "eta_real_s": 0.0,
    "signature_valid": true,
    "reject_reason": null,
    "size_bytes": 2310
  },
  "… încă 1 elemente de același fel"
]
```

</details>

---

#### `GET /api/v1/link/packets/{packet_id}` — Un pachet, cu conținutul decriptat

**Cine poate apela:** ofițer medical (cmo), Pământ (earth)

`payload` apare doar pentru pachetele `delivered`. Rolul `earth` vede conținutul pachetelor `down` ajunse;
rolul `cmo` vede conținutul pachetelor `up` ajunse și al celor trimise de el. Altfel `payload` e `null`.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `packet_id` | cale | text | da |  |

**Răspuns 200:** [PacketDetail](#packetdetail)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>earth</code>)</summary>

```http
GET /api/v1/link/packets/pk-0006
```

Răspuns `200`:

```json
{
  "id": "pk-0006",
  "seq": 6,
  "direction": "down",
  "kind": "weekly_summary",
  "status": "delivered",
  "title": "Rezumat săptămânal aprobat de astronaut",
  "sender": "Specialist de misiune 2",
  "level": null,
  "alert_status": null,
  "crew_id": "cm-2",
  "alert_id": null,
  "in_reply_to": null,
  "created_at": "2027-04-14T09:20:00Z",
  "sent_at": "2027-04-14T09:29:00Z",
  "arrives_at": "2027-04-14T09:41:00Z",
  "delivered_at": "2027-04-14T09:41:00Z",
  "progress": 1.0,
  "eta_real_s": 0.0,
  "signature_valid": true,
  "reject_reason": null,
  "size_bytes": 2310,
  "payload": {
    "summary": "Săptămâna 13: somn mediu 6,1 h, 6 check-in-uri din 7, nicio alertă de nivel 3."
  },
  "crypto": {
    "cipher": "AES-256-GCM",
    "signature_alg": "Ed25519",
    "key_id": "ship-2026-01",
    "nonce_b64": "q83vEjRWeJCrze8S",
    "signature_b64": "MEUCIQDc...trunchiat..."
  }
}
```

</details>

---

#### `POST /api/v1/link/outbox` — Pune un mesaj în coada spre Pământ

**Cine poate apela:** astronaut, ofițer medical (cmo)

Pentru rezumatul săptămânal aprobat de astronaut (`weekly_summary`). Alertele de nivel 3 intră în coadă automat,
prin `/alerts/{id}/escalate`; folosiți `alert_l3` aici doar pentru retrimitere.

Astronautul poate trimite doar despre propriul `crew_id`. Pachetul pornește `queued` și pleacă la următoarea
fereastră de comunicare.

**SSE:** `packet.sent` când pleacă, `packet.arrived` când ajunge.

**Corpul cererii:** [OutboxCreate](#outboxcreate)

**Răspuns 201:** [Packet](#packet)

**Erori posibile:** 401, 403, 404, 422 — forma din secțiunea [Erori](#5-erori).

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
  "id": "pk-0008",
  "seq": 8,
  "direction": "down",
  "kind": "weekly_summary",
  "status": "queued",
  "title": "Rezumat săptămânal aprobat de astronaut",
  "sender": "Specialist de misiune 2",
  "level": null,
  "alert_status": null,
  "crew_id": "cm-2",
  "alert_id": null,
  "in_reply_to": null,
  "created_at": "2027-04-15T07:42:00Z",
  "sent_at": null,
  "arrives_at": null,
  "delivered_at": null,
  "progress": 0.0,
  "eta_real_s": null,
  "signature_valid": null,
  "reject_reason": null,
  "size_bytes": 2048
}
```

</details>

---

#### `POST /api/v1/earth/replies` — Răspunsul medicului de pe Pământ

**Cine poate apela:** Pământ (earth)

Butonul „Pune în coadă, criptat” din Controlul misiunii. Răspunsul pleacă la următoarea fereastră și ajunge la
bord după `one_way_delay_s`. Când ajunge, apare în `/crew/{id}/messages` și în `earth_reply` al alertei.

**SSE:** `packet.sent`, apoi `packet.arrived` (cu `crew_id`) la sosire.

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
  "in_reply_to": "pk-0007",
  "crew_id": "cm-2",
  "alert_id": "al-1042",
  "body": "De acord cu odihna. Temperatura de două ori pe zi; dacă depășește 38 °C, anunțați-ne."
}
```

Răspuns `201`:

```json
{
  "id": "pk-0009",
  "seq": 9,
  "direction": "up",
  "kind": "earth_reply",
  "status": "queued",
  "title": "Răspuns: De acord cu odihna. Temperatura de două ori pe zi; dacă depă",
  "sender": "Medicul de zbor",
  "level": null,
  "alert_status": null,
  "crew_id": "cm-2",
  "alert_id": "al-1042",
  "in_reply_to": "pk-0007",
  "created_at": "2027-04-15T07:42:00Z",
  "sent_at": null,
  "arrives_at": null,
  "delivered_at": null,
  "progress": 0.0,
  "eta_real_s": null,
  "signature_valid": null,
  "reject_reason": null,
  "size_bytes": 605
}
```

</details>

---

#### `GET /api/v1/crew/{crew_id}/messages` — Mesaje sosite de pe Pământ

**Cine poate apela:** astronaut, ofițer medical (cmo)

Răspunsurile medicului de zbor și avertizările DONKI care AU AJUNS la bord, deja decriptate și verificate.
Cele încă pe drum nu apar aici.

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
[
  {
    "packet_id": "pk-0004",
    "kind": "earth_reply",
    "sender": "Medicul de zbor",
    "body": "Am primit rezumatul. Continuați planul de somn; revenim la următoarea fereastră.",
    "sent_at": "2027-04-13T12:00:00Z",
    "delivered_at": "2027-04-13T12:12:00Z",
    "alert_id": null,
    "donki_event_id": null,
    "read": true
  }
]
```

</details>

---

### 9. Radiații și furtuna solară

#### `GET /api/v1/radiation/status` — Starea radiațiilor acum

**Cine poate apela:** astronaut, ofițer medical (cmo)

Rata dozei la dozimetrul de la bord, media pe 24 h, dacă e alertă și dacă echipajul e în adăpost.

`lead_minutes` se completează când sosește avertizarea DONKI de pe Pământ: e numărul de minute cu care SHADOW a
fost mai rapid. Afișați-l mare; e cifra din pitch.

Rolul `earth` NU are acces: Pământul nu vede dozimetrul navei în timp real, ci doar ce ajunge prin coadă.

**Răspuns 200:** [RadiationStatus](#radiationstatus)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/radiation/status
```

Răspuns `200`:

```json
{
  "at": "2027-04-15T07:42:00Z",
  "dose_rate_usv_h": 66.4,
  "mean_24h_usv_h": 65.8,
  "ratio": 1.01,
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

#### `GET /api/v1/radiation/series` — Curba dozei (grafic)

**Cine poate apela:** astronaut, ofițer medical (cmo)

Punctele pentru graficul dozei. Reîncărcați la SSE `radiation.reading` (vine cel mult o dată la 2 secunde reale).

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `hours` | query | număr | nu | Câte ore de misiune în urmă. Implicit: `24`. (max 240; > 0) |
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
      "t": "2027-04-15T06:52:00Z",
      "dose_rate_usv_h": 65.8,
      "mean_24h_usv_h": 66.0,
      "sheltered": false
    },
    {
      "t": "2027-04-15T07:02:00Z",
      "dose_rate_usv_h": 66.2,
      "mean_24h_usv_h": 66.0,
      "sheltered": false
    },
    "… încă 4 elemente de același fel"
  ]
}
```

</details>

---

#### `GET /api/v1/radiation/events` — Evenimentele DONKI disponibile

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Evenimentele reale NASA DONKI încărcate din fișier (offline). Momentan unul: 11 mai 2024.

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
    "note": "GLE 74, furtuna Gannon (mai 2024)"
  }
]
```

</details>

---

#### `POST /api/v1/radiation/shelter-ack` — „Sunt în adăpost”

**Cine poate apela:** astronaut, ofițer medical (cmo)

Astronautul confirmă că a ajuns în adăpost (sau că a ieșit). Din acest moment simulatorul aplică factorul de
ecranare, iar ora se salvează pentru calculul `lead_minutes`.

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
  "at": "2027-04-15T07:42:00Z",
  "dose_rate_usv_h": 66.4,
  "mean_24h_usv_h": 65.8,
  "ratio": 1.01,
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

### 10. Medicul AI

#### `GET /api/v1/ai/status` — Starea modelului

**Cine poate apela:** astronaut, ofițer medical (cmo)

Dacă modelul local e încărcat. Când `ready` e `false`, cardul AI afișează doar textul din catalog.

**Răspuns 200:** [AiStatus](#aistatus)

**Erori posibile:** 401, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/ai/status
```

Răspuns `200`:

```json
{
  "ready": true,
  "model": "mock",
  "mode": "mock"
}
```

</details>

---

#### `POST /api/v1/ai/chat` — Întreabă medicul AI

**Cine poate apela:** astronaut, ofițer medical (cmo)

Răspuns scurt, cu surse NASA (RAG), care reformulează recomandarea din catalog. **AI-ul nu decide triajul.**

* Poate dura 5–15 secunde pe laptop: afișați o stare de încărcare.
* Dacă modelul nu răspunde în 20 de secunde sau e oprit, endpoint-ul NU dă eroare: întoarce textul din catalog,
  cu `fallback = true`. Aplicația merge și fără AI.
* Astronautul poate întreba doar despre propriul `crew_id`.

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
  "alert_id": "al-1042",
  "history": []
}
```

Răspuns `200`:

```json
{
  "answer": "Pulsul tău de noapte e cu 7 bpm peste normalul tău de trei nopți. Corpul face asta des când luptă cu o infecție, înainte să apară simptome. Recomandarea e să anunți ofițerul medical, să-ți protejezi somnul și să măsori temperatura de două ori pe zi.",
  "citations": [
    {
      "title": "Alavi et al. (2022), Nature Medicine",
      "url": "https://www.nature.com/articles/s41591-021-01593-2",
      "snippet": "Alerta roșie: puls de repaus nocturn cu cel puțin 4 bpm peste baseline, două nopți consecutive."
    },
    {
      "title": "NASA HRP — Risk of Altered Immune Response",
      "url": "https://humanresearchroadmap.nasa.gov/Risks/?i=85",
      "snippet": "Stresul zborului, somnul perturbat și radiațiile dereglează sistemul imunitar."
    }
  ],
  "recommendation_ids": [
    "immune-2-1"
  ],
  "model": "gemma-3-4b-it-Q4_K_M",
  "latency_ms": 2140,
  "fallback": false,
  "disclaimer": "Prototip de sprijin, nu dispozitiv medical."
}
```

</details>

---

### 11. Securitate și dovezi

#### `GET /api/v1/access-log` — Jurnalul de acces

**Cine poate apela:** astronaut, ofițer medical (cmo)

Cine a citit ce. Astronautul vede cine i-a accesat datele; ofițerul medical vede tot jurnalul.
Jurnalul doar se adaugă: fiecare intrare conține hash-ul celei dinainte (`prev_hash`), deci nu poate fi modificat pe ascuns.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `crew_id` | query | text \| null | nu | Astronaut: se ignoră, vede mereu doar accesul la datele lui. |
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
    "id": 1,
    "at": "2027-04-15T06:31:00Z",
    "actor": "Ofițer medical de bord",
    "actor_role": "cmo",
    "action": "read_alert",
    "resource": "alerts/al-1042",
    "crew_id": "cm-2",
    "outcome": "allowed",
    "prev_hash": "0000000000000000",
    "hash": "9f2c41d07ab3e5c8"
  },
  {
    "id": 2,
    "at": "2027-04-15T06:40:00Z",
    "actor": "Comandant",
    "actor_role": "astronaut",
    "action": "read_dashboard",
    "resource": "crew/cm-2/dashboard",
    "crew_id": "cm-2",
    "outcome": "denied",
    "prev_hash": "9f2c41d07ab3e5c8",
    "hash": "1b77e0aa52c9d4f3"
  }
]
```

</details>

---

#### `GET /api/v1/security/rejections` — Date și pachete respinse

**Cine poate apela:** astronaut, ofițer medical (cmo)

Valorile imposibile, senzorii „înghețați”, semnăturile invalide și pachetele retrimise.

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
[
  {
    "id": "rj-0003",
    "at": "2027-04-14T03:12:00Z",
    "kind": "bad_signature",
    "source": "senzor-07",
    "crew_id": null,
    "metric_key": "temperature_c",
    "value": 41.9,
    "message": "Temperatură 41,9 °C · semnătură invalidă"
  },
  {
    "id": "rj-0002",
    "at": "2027-04-12T14:00:00Z",
    "kind": "frozen_sensor",
    "source": "wearable-cm-4",
    "crew_id": "cm-4",
    "metric_key": "night_pulse_bpm",
    "value": 57.0,
    "message": "Aceeași valoare 240 de citiri la rând: senzor înghețat"
  }
]
```

</details>

---

#### `POST /api/v1/ingest/measurements` — Primește o măsurătoare de la un dispozitiv

**Cine poate apela:** dispozitiv (semnătură Ed25519, fără JWT)

**Nu e pentru frontend.** Îl apelează simulatorul și dispozitivele. Nu folosește JWT: autentificarea este
semnătura Ed25519 a dispozitivului, verificată cu cheia publică înregistrată pentru `device_id`.

Verificări, în ordine: semnătura → plauzibilitatea valorii → senzor înghețat (aceeași valoare de prea multe ori).
O măsurătoare respinsă întoarce tot 200, cu `accepted = false`, și apare în `/security/rejections`.

**SSE:** `measurement.rejected` la respingere.

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
  "accepted": true,
  "rejection": null
}
```

</details>

---

#### `GET /api/v1/evidence/tests` — Rezultatele testelor automate

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Ultimul raport pytest pe motorul de protocoale, pentru ecranul Evidence.

**Răspuns 200:** [TestReport](#testreport)

**Erori posibile:** 401, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>specialist2</code>)</summary>

```http
GET /api/v1/evidence/tests
```

Răspuns `200`:

```json
{
  "ran_at": "2027-04-15T00:05:00Z",
  "passed": 3,
  "failed": 0,
  "skipped": 0,
  "duration_s": 1.42,
  "tests": [
    {
      "name": "test_nightsignal_red_after_two_nights",
      "module": "tests/test_immune.py",
      "outcome": "passed",
      "duration_ms": 12.1
    },
    {
      "name": "test_sep_alert_at_2x_mean",
      "module": "tests/test_radiation.py",
      "outcome": "passed",
      "duration_ms": 8.4
    },
    "… încă 1 elemente de același fel"
  ]
}
```

</details>

---

#### `GET /api/v1/evidence/parameters` — Pragurile și sursele lor

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Conținutul `parameters.json`: fiecare prag cu valoare, unitate, explicație și sursă, marcat verificat/neverificat și publicat/derivat.

| Parametru | Unde | Tip | Obligatoriu | Descriere |
|---|---|---|---|---|
| `topic` | query | text \| null | nu | comportamental / cardiovascular / imunitar / oase_muschi / radiatii / comunicare |
| `key_only` | query | true/false | nu | Doar pragurile folosite direct de motorul de triaj. Implicit: `False`. |

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
    "name": "Sesiuni consecutive necesare pentru detecție continuă",
    "value": 4,
    "unit": "sesiuni de tastare",
    "explanation": "În modul de detecție continuă (quick change detection), modelul detectează oboseala după 4 sesiuni cu AUC 80% (EER 20%). Sugerează ca alerta să ceară o abatere susținută pe mai multe sesiuni, nu una izolată.",
    "is_key_threshold": true,
    "source": {
      "citation": "Acien A, Morales A, Vera-Rodriguez R, Fierrez J, Mondesire-Crump I, Arroyo-Gallego T. (2022). Detection of Mental Fatigue in the General Population: Feasibility Study of Keystroke Dynamics as a Real-world Biomarker. JMIR Biomedical Engineering 7(2):e41003 (publicat 21.11.2022).",
      "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11041424/",
      "verification": "verified",
      "derivation": "published",
      "evidence_strength": "slabă"
    }
  },
  {
    "id": "keystroke_baseline_duration",
    "topic": "comportamental",
    "name": "Durata minimă a baseline-ului de tastare",
    "value": 7,
    "unit": "zile",
    "explanation": "Nicio sursă citită nu stabilește un număr minim de zile/sesiuni pentru un baseline stabil de tastare. Propunere de lucru: ≥7 zile care acoperă toate momentele zilei (viteza are ritm diurn), cu normalizare pe intervalul orar.",
    "is_key_threshold": true,
    "source": {
      "citation": "Fang Y, Yang P, Frank E, Goldstein C, Wright AGC, Bohnert ASB, et al. (2026). Patterns of smartphone typing performance by time awake: implications for unobtrusive ambulatory mental fatigue assessment. PLOS Digital Health 5(3):e0001281.",
      "url": "https://journals.plos.org/digitalhealth/article?id=10.1371/journal.pdig.0001281",
      "verification": "unverified",
      "derivation": "derived",
      "evidence_strength": "slabă"
    }
  },
  "… încă 31 elemente de același fel"
]
```

</details>

---

### 12. Demo și simulator

#### `POST /api/v1/sim/sep/start` — Pornește furtuna solară

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Butonul de demo. Simulatorul redă evenimentul real din DONKI:

1. rata dozei la dozimetru urcă → la 3 citiri peste 2× media, SHADOW dă alerta de nivel 1 (`radiation.alert`);
2. avertizarea de pe Pământ pleacă în coadă ca pachet `donki_alert`, direcția `up`, și ajunge după întârzierea legăturii;
3. la sosire se completează `lead_minutes` în `/radiation/status`.

**SSE:** `radiation.alert`, `alert.created`, `radiation.reading`, `packet.sent`, apoi `packet.arrived`.

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
  "at": "2027-04-15T07:42:00Z",
  "dose_rate_usv_h": 412.0,
  "mean_24h_usv_h": 66.0,
  "ratio": 6.24,
  "threshold_ratio": 2.0,
  "alert_active": true,
  "alert_id": "al-1050",
  "sheltered": false,
  "sheltered_since": null,
  "event": {
    "donki_id": "2024-05-11T02:10:00-SEP-001",
    "event_time": "2024-05-11T02:10:00Z",
    "sim_onset_at": "2027-04-15T07:33:00Z",
    "instrument": "GOES-P: SEISS >100 MeV",
    "flare_class": "X5.8",
    "cme_id": "2024-05-11T01:36:00-CME-001",
    "donki_url": "https://ccmc.gsfc.nasa.gov/DONKI/view/SEP/30714/-1",
    "note": "GLE 74, furtuna Gannon (mai 2024)"
  },
  "event_dose_msv": 0.05,
  "onboard_alert_at": "2027-04-15T07:35:00Z",
  "earth_warning_arrived_at": null,
  "lead_minutes": null,
  "profile_is_synthetic": true
}
```

</details>

---

#### `POST /api/v1/sim/sep/stop` — Oprește furtuna solară

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Readuce rata dozei la fond. **SSE:** `radiation.cleared`.

**Răspuns 200:** [RadiationStatus](#radiationstatus)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>medic</code>)</summary>

```http
POST /api/v1/sim/sep/stop
```

Răspuns `200`:

```json
{
  "at": "2027-04-15T07:42:00Z",
  "dose_rate_usv_h": 66.4,
  "mean_24h_usv_h": 65.8,
  "ratio": 1.01,
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

#### `POST /api/v1/demo/inject-spoof` — Injectează un pachet falsificat

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Demo de securitate: pune în coadă un pachet semnat cu o cheie greșită. La sosire e respins și apare cu
`status = rejected`, `signature_valid = false`, în jurnal și în `/security/rejections`.

**SSE:** `packet.rejected`.

**Răspuns 200:** [Packet](#packet)

**Erori posibile:** 401, 403, 422 — forma din secțiunea [Erori](#5-erori).

<details><summary>Exemplu (autentificat ca <code>earth</code>)</summary>

```http
POST /api/v1/demo/inject-spoof
```

Răspuns `200`:

```json
{
  "id": "pk-0005",
  "seq": 5,
  "direction": "down",
  "kind": "alert_l3",
  "status": "rejected",
  "title": "Temperatură 41,9 °C · senzor 07",
  "sender": "necunoscut",
  "level": null,
  "alert_status": null,
  "crew_id": null,
  "alert_id": null,
  "in_reply_to": null,
  "created_at": "2027-04-14T03:12:00Z",
  "sent_at": "2027-04-14T03:12:00Z",
  "arrives_at": "2027-04-14T03:24:00Z",
  "delivered_at": null,
  "progress": 1.0,
  "eta_real_s": 0.0,
  "signature_valid": false,
  "reject_reason": "bad_signature",
  "size_bytes": 612
}
```

</details>

---

#### `POST /api/v1/demo/frozen-sensor` — Simulează un senzor înghețat

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Demo de securitate: simulatorul trimite aceeași valoare de multe ori; stratul de validare o respinge.

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
  "at": "2027-04-12T14:00:00Z",
  "kind": "frozen_sensor",
  "source": "wearable-cm-4",
  "crew_id": "cm-4",
  "metric_key": "night_pulse_bpm",
  "value": 57.0,
  "message": "Aceeași valoare 240 de citiri la rând: senzor înghețat"
}
```

</details>

---

#### `POST /api/v1/sim/reset` — Readuce demo-ul la starea inițială

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Șterge tot ce s-a schimbat în timpul demo-ului și reîncarcă scenariul: baza se recreează, istoricul se
regenerează (același seed, deci aceleași date), ceasul repornește la ziua 96, ora 07:00, iar blocările de
cont se șterg. Durează câteva secunde. Folosiți-l între repetiții.

După reset, frontend-ul trebuie să reîncarce tot (ca după o reconectare). Tokenurile rămân valabile.

**SSE:** `mission.tick` cu ziua 96, apoi `dashboard.changed`.

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

### 13. Evenimente live (SSE)

#### `GET /api/v1/events` — Fluxul de evenimente live

**Cine poate apela:** astronaut, ofițer medical (cmo), Pământ (earth)

Conexiune Server-Sent Events, ținută deschisă cât e aplicația pornită. **Înlocuiește polling-ul.**

* Autentificare cu același antet `Authorization`. `EventSource` din browser nu poate trimite antete, deci folosiți
  `@microsoft/fetch-event-source` (exemplu în README).
* Fiecare utilizator primește doar evenimentele la care are dreptul: astronautul doar pe ale lui și pe cele
  generale; `earth` doar `mission.tick`, `environment.changed` și `packet.*`.
* La 15 secunde fără evenimente vine un comentariu `: ping`, ca să nu se închidă conexiunea.
* La reconectare, reîncărcați datele ecranului curent; evenimentele pierdute nu se retrimit.

Lista tipurilor și forma câmpului `data` pentru fiecare: README, secțiunea „Evenimente live”.

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
| `username` | text | da |  Ex.: `"specialist2"` |
| `password` | text | da | Parola PERSONALĂ a contului. Fiecare cont are altă parolă. (lungime min 1) Ex.: `"<parola din seed>"` |

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
| `duration_s` | număr întreg | nu | PVT-B durează 3 minute. |
| `trials` | listă de [PvtTrial](#pvttrial) | da |  (min elemente 1) |

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
| `exercise` | text | da |  Ex.: `"genuflexiuni ARED"` |
| `reps` | număr întreg | da |  (min 1.0) Ex.: `10` |
| `load_kg` | număr | da |  (min 0.0) Ex.: `85` |

#### ExerciseSessionCreate

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `kind` | `"resistance"` \| `"aerobic"` | da |  |
| `started_at` | dată-oră (ISO 8601) | da |  |
| `duration_min` | număr | da |  (> 0.0) Ex.: `40` |
| `sets` | listă de [ExerciseSet](#exerciseset) | nu | Gol pentru sesiuni aerobe. |

#### ExerciseSession

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `kind` | `"resistance"` \| `"aerobic"` | da |  |
| `started_at` | dată-oră (ISO 8601) | da |  |
| `duration_min` | număr | da |  (> 0.0) Ex.: `40` |
| `sets` | listă de [ExerciseSet](#exerciseset) | nu | Gol pentru sesiuni aerobe. |
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
| `kind` | `"weekly_summary"` \| `"alert_l3"` | da |  |
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
| `event_id` | text | nu |  |
| `starts_in_min` | număr | nu | Peste câte minute de MISIUNE începe furtuna. (min 0.0) |

#### ChatMessage

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `role` | `"user"` \| `"assistant"` | da |  |
| `content` | text | da |  |

#### AiChatRequest

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `crew_id` | text | da |  Ex.: `"cm-2"` |
| `message` | text | da |  (lungime min 1; lungime max 1000) Ex.: `"De ce mi-a crescut pulsul de noapte?"` |
| `alert_id` | text \| null | nu | Dacă întrebarea e despre o alertă anume. Ex.: `"al-1042"` |
| `history` | listă de [ChatMessage](#chatmessage) | nu | Ultimele max. 6 mesaje. |

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
| `device_id` | text | da |  Ex.: `"wearable-cm-2"` |
| `crew_id` | text | da |  Ex.: `"cm-2"` |
| `metric_key` | text | da |  Ex.: `"night_pulse_bpm"` |
| `value` | număr | da |  Ex.: `61` |
| `unit` | text | da |  Ex.: `"bpm"` |
| `measured_at` | dată-oră (ISO 8601) | da |  |
| `signature_b64` | text | da | Ed25519 peste JSON-ul canonic al celorlalte câmpuri (chei sortate, fără spații). |

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

