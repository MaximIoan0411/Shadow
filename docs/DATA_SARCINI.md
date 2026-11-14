# Data — ce trebuie pregătit

**Folder:** `data/` · **Fără cod.** Doar fișiere pe care le citesc backend-ul și serviciul AI.

Aici stă tot ce e **conținut**, nu logică: pragurile, recomandările, textele explicative, evenimentul solar real,
mediile și scenariul misiunii. Sunt separate de cod din trei motive: se pot corecta fără să atingi programul,
fiecare cifră își păstrează sursa lângă ea, iar juriul poate verifica de unde vine orice valoare.

**Cine se ocupă:** nu e o echipă separată. Un om de pe backend ține folderul; cel de pe AI citește din el. Orice
schimbare de **format** se anunță, fiindcă strică încărcarea la pornire.

**Stare (contract 1.2): toate cele 7 fișiere există** și trec validarea. Formatul lor e definit în
`backend/app/datafiles.py` și documentat în `contract/data/README.md`; mock-ul backend-ului le citește deja.
Ce rămâne: corecturi de conținut, pașii (`steps`) pentru restul recomandărilor și reglarea scenariului.

**Regula de bază: nicio cifră fără sursă.** Dacă o valoare e aleasă de echipă, e marcată „derivat”. Dacă nu a
putut fi verificată, e marcată „NEVERIFICAT” și se prezintă ca ipoteză.

**Priorități:** `P0` = backend-ul nu pornește fără el · `P1` = necesar până la ora 10 · `P2` = bonus.

## Cuprins

1. [parameters.json](#1-parametersjson-p0)
2. [Catalogul de recomandări](#2-catalogul-de-recomandări-p0)
3. [Textele check-in-ului](#3-textele-check-in-ului-p0)
4. [Funcțiile părților corpului](#4-funcțiile-părților-corpului-p0)
5. [Mediile](#5-mediile-p0)
6. [Evenimentul solar](#6-evenimentul-solar-p1)
7. [Scenariul misiunii](#7-scenariul-misiunii-p1)
8. [Ce NU stă aici](#8-ce-nu-stă-aici)
9. [Ordinea de lucru](#9-ordinea-de-lucru)
10. [Cu cine te legi](#10-cu-cine-te-legi)
11. [Scheletul gol](#11-scheletul-gol)

---

## 1. parameters.json (P0)

**Există deja** (din research): 169 de parametri, 143 verificați pe sursă, 25 derivați. Se pune în `data/` așa cum e.

- **La ce folosește:** pragurile motorului de triaj și ecranul Evidence.
- **Structura:** `meta`, `praguri_cheie_triaj` (lista celor 33 de praguri pe care le folosește efectiv motorul),
  `piloni` (toți parametrii, cu sursă), `eveniment_sep_simulator`, `corecturi_plan`, `note_dovezi_slabe`.
- **Un parametru arată așa:**

```json
{
  "id": "nightsignal_red_delta_bpm",
  "nume": "NightSignal: prag roșu",
  "valoare": 4,
  "unitate": "bpm peste mediana personală",
  "explicatie": "…",
  "status": "VERIFICAT",
  "derivare": "publicat",
  "forta_dovezii": "moderată",
  "sursa": { "citare": "Alavi et al. (2022)…", "doi": "…", "url": "…" }
}
```

- **De făcut:**
  - `keystroke_baseline_duration` are valoarea `null`: puneți 7 și lăsați marcajul „derivat”;
  - verificați că toate cele 33 de id-uri din `praguri_cheie_triaj` există în `piloni`;
  - nu schimbați valori fără să schimbați și sursa.
- **Atenție:** `valoare` are tipuri diferite (număr, text, listă, dicționar, `null`). Backend-ul trebuie să accepte
  toate tipurile la încărcare.
- **Gata când:** backend-ul îl încarcă la pornire fără eroare.

## 2. Catalogul de recomandări (P0)

`data/catalog/recommendations.json`. Varianta de citit există (`catalog_recomandari_texte.md`, din research);
trebuie transformată într-un fișier pe care îl poate citi programul.

- **La ce folosește:** triajul alege din el recomandarea unei alerte; medicul AI o reformulează; serviciul AI îl
  pune și în corpusul de documente.
- **O recomandare arată așa** (forma modelului `Recommendation` din contract, plus două câmpuri folosite doar de
  backend ca să construiască planul alertei: `steps` și `recheck_days`):

```json
{
  "id": "immune-2-1",
  "topic": "immune",
  "level": 2,
  "trigger": "Puls mediu de noapte ≥ +4 bpm peste mediana personală, două nopți la rând.",
  "action": "Anunță ofițerul medical de la bord, cu graficul de puls și temperatură și jurnalul de simptome.",
  "steps": [
    "Culcă-te cu o oră mai devreme în următoarele 3 nopți.",
    "Măsoară temperatura dimineața și seara.",
    "Completează jurnalul de simptome."
  ],
  "recheck_days": 2,
  "hrp_risk": "Risk of Adverse Health Events due to Altered Immune Response",
  "hrp_risk_url": "https://humanresearchroadmap.nasa.gov/Risks/?i=85",
  "source": {
    "citation": "Alavi et al. (2022), Nature Medicine 28:175–184",
    "url": "https://www.nature.com/articles/s41591-021-01593-2",
    "verification": "verified",
    "derivation": "published",
    "evidence_strength": "moderată"
  }
}
```

- **Reguli:**
  - `id` = `<topic>-<nivel>-<număr>`; `topic` ∈ `behavioral`, `cardio`, `immune`, `musculoskeletal`, `radiation`;
  - `level` ∈ 1, 2, 3 (1 = singur, 2 = ofițerul medical, 3 = Pământul);
  - `steps` = pașii planului de acțiune afișați cu bife: 2–4 pași scurți, concreți, pe care astronautul îi poate
    face la bord;
  - `recheck_days` între 1 și 3;
  - intrările marcate ⚠ în catalogul din research primesc `"verification": "unverified"`;
  - textul nu numește medicamente sau doze: aplicația nu le recomandă.
- **Minimum pentru demo:** câte o recomandare pe fiecare nivel pentru `immune` și `behavioral`, plus
  `radiation-1-1` (adăpostul). Restul se adaugă pe parcurs.
- **Gata când:** `GET /catalog/recommendations` întoarce conținutul fișierului.

## 3. Textele check-in-ului (P0)

`data/texts/checkin_indicators.json`. Există acum în codul mock (`backend/app/examples.py`, `CHECKIN_SCHEMA`);
se mută aici.

- **La ce folosește:** frontend-ul construiește formularul din el, prin `GET /checkin/schema`.
- **Un indicator arată așa** (aceeași formă ca modelul `CheckinIndicator`):

```json
{
  "key": "temperature_c",
  "label": "Temperatura",
  "unit": "°C",
  "input": "number",
  "min": 34,
  "max": 41.5,
  "step": 0.1,
  "how_to_measure": "Cu termometrul, la aceeași oră în fiecare zi.",
  "what_it_means": "O creștere față de normalul tău poate semnala o infecție.",
  "why_in_space": "Într-un spațiu închis, o infecție se poate transmite întregului echipaj.",
  "pillar": "immune",
  "source": { "citation": "…", "url": "…" }
}
```

- **Indicatorii:** starea de spirit, tensiunea (sistolică și diastolică), pulsul, glicemia, temperatura, somnul,
  mesele de ieri. Textele „de ce contează în spațiu” sunt în catalogul din research, secțiunea 4.
- **Reguli:**
  - `min` și `max` sunt limitele **fizic posibile**, nu cele normale: în afara lor valoarea e respinsă ca
    imposibilă; aceleași limite le folosește și validarea echipei de securitate;
  - fiecare text are cel mult două propoziții;
  - unde dovezile sunt slabe (glicemia), textul o spune.
- **Gata când:** formularul de check-in arată textele din acest fișier.

## 4. Funcțiile părților corpului (P0)

`data/texts/body_functions.json`. Cerință din brief: la click pe o zonă, aplicația explică funcția acelei părți.

```json
{
  "immune": {
    "name": "Santinela",
    "body_zone": "immune",
    "function_text": "Sistemul imunitar apără corpul de virusuri, bacterii și celule anormale. În zbor, stresul, somnul perturbat și radiațiile îl dereglează.",
    "hazard": "hostile_environment",
    "hazard_text": "Radiațiile și mediul închis: stresul și spațiul comun slăbesc apărarea organismului.",
    "limits_text": "Algoritmul nu distinge tipul de infecție și poate da alarme false. A fost validat pe civili, nu pe astronauți.",
    "sources": [ { "citation": "…", "url": "…" } ]
  }
}
```

- **Câte o intrare pentru:** `behavioral` (creier), `cardio` (inimă), `immune`, `musculoskeletal` (oase și mușchi).
- **Textele** sunt în catalogul din research, secțiunea 3. La oase, folosiți varianta corectată: fără exerciții
  1–1,5% pe lună; cu exercițiul cu greutăți de pe ISS, circa 0,3–0,6% pe lună.
- **`hazard`** ∈ `radiation`, `isolation`, `distance`, `gravity`, `hostile_environment` (cele 5 pericole NASA).
- **Gata când:** panoul fiecărei zone începe cu textul din acest fișier.

## 5. Mediile (P0)

`data/environments.json`. Există acum în codul mock; se mută aici.

| `id` | Nume | Întârziere într-un sens | Gravitație | Doză de fond |
|---|---|---|---|---|
| `iss` | Stația spațială | 1 s | 0 g | 0,731 mSv/zi |
| `moon_base` | Bază pe Lună | 1,3 s | 0,165 g | 1,369 mSv/zi |
| `mars_transit` | Tranzit spre Marte | 3–22 min (în demo: 700 s) | 0 g | 1,58 mSv/zi |
| `mars_base` | Bază pe Marte | 3–22 min (în demo: 700 s) | 0,38 g | 0,64 mSv/zi (neverificat) |

- Valorile vin din `parameters.json`; fiecare mediu își păstrează sursa.
- Fișierul mai conține, pe fiecare mediu: pericolele evidențiate și o descriere de o propoziție.
- **Gata când:** comutatorul de mediu arată cele patru medii din fișier.

## 6. Evenimentul solar (P1)

`data/donki/donki_sep_event.json`. **Există deja** (din research); se pune aici așa cum e.

- **Ce este:** evenimentul real de particule solare din 11 mai 2024 (furtuna Gannon), din baza NASA DONKI.
- **Ce folosește simulatorul din el:** orele reale (erupția la 01:10Z, particulele la 02:10Z, alertele NASA la
  02:30Z și 02:46Z), identificatorii și linkul DONKI.
- **Ce NU conține:** doza măsurată pe stație pentru acest eveniment (nu e publicată). De aceea forma curbei din
  simulator e sintetică și marcată ca atare.
- **Gata când:** `GET /radiation/events` întoarce evenimentul din fișier, fără internet.

## 7. Scenariul misiunii (P1)

`data/scenario/scenario.json`. Descrie ce se întâmplă în cele 140 de zile, ca simulatorul să nu aibă evenimente
scrise în cod.

```json
{
  "seed": 2026,
  "total_days": 140,
  "start": "2027-01-10T00:00:00Z",
  "crew_baselines": {
    "cm-1": { "night_pulse_bpm": 58, "sleep_hours": 6.4, "temperature_c": 36.8 },
    "cm-2": { "night_pulse_bpm": 54, "sleep_hours": 6.6, "temperature_c": 36.9 }
  },
  "events": [
    { "days": [40, 41], "crew": "all", "kind": "poor_sleep", "note": "cauză de mediu" },
    { "days": [93, 100], "crew": "cm-2", "kind": "infection_onset", "note": "boală prinsă înainte de simptome" },
    { "days": [97, 97], "crew": "all", "kind": "solar_storm", "event_id": "2024-05-11T02:10:00-SEP-001" }
  ]
}
```

- **Evenimentele obligatorii** sunt cele din tabelul din `BACKEND_SARCINI.md`, secțiunea 4.
- **Reguli:** același `seed` dă mereu aceleași date; fiecare membru are alt normal personal; toate valorile
  generate sunt marcate „simulat”.
- **Gata când:** schimbarea unei zile în fișier mută evenimentul pe derulator, fără nicio schimbare în cod.

## 8. Ce NU stă aici

| Ce | Unde stă | De ce |
|---|---|---|
| conturile de test | `backend/seed/users.json` | țin de autentificare |
| cheile | nicăieri în git | secrete |
| documentele NASA pentru AI | `ai/corpus/` | sunt mari și le folosește doar serviciul AI |
| modelele | `ai/models/` | nu intră în git |
| baza de date | se creează la pornire | conține date generate |
| cod | `backend/`, `ai/` | `data/` nu are niciun fișier `.py` |

## 9. Ordinea de lucru

| Ore | Ce |
|---|---|
| 0–1 | `parameters.json` și `donki_sep_event.json` puse în folder; formatul fiecărui fișier confirmat cu backend-ul |
| 1–3 | `environments.json`, `checkin_indicators.json`, `body_functions.json` (mutate din codul mock) |
| 2–6 | `recommendations.json`: minimumul pentru demo |
| 6–10 | `scenario.json`; restul recomandărilor |
| 10–16 | corecturi după integrare; verificarea surselor care apar pe ecran |

## 10. Cu cine te legi

| Cu cine | Ce citește | Fișiere | Când se stabilește |
|---|---|---|---|
| **Backend** | tot | toate fișierele; le încarcă și le validează la pornire | ora 0–1: formatul fiecărui fișier |
| **AI** | catalogul și sursele, pentru corpus și pentru citări | `catalog/recommendations.json`, `parameters.json` | ora 0–2 |
| **Securitate** | limitele fizic posibile ale fiecărei metrici, pentru validare | `texts/checkin_indicators.json` (`min`, `max`) | ora 2–6 |
| **Frontend** | nimic direct: textele ajung la el prin backend | — | — |

Orice schimbare de **format** (un câmp redenumit, un tip schimbat) se anunță înainte. O schimbare de **conținut**
(un text corectat, un prag actualizat cu sursa lui) se poate face oricând.

## 11. Scheletul gol

```
data/
├── README.md
├── parameters.json                      există, din research
├── environments.json
├── catalog/
│   ├── recommendations.json
│   └── catalog_recomandari_texte.md     există, din research
├── texts/
│   ├── checkin_indicators.json
│   └── body_functions.json
├── donki/
│   └── donki_sep_event.json             există, din research
└── scenario/
    └── scenario.json
```
