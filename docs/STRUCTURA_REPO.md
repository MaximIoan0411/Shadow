# SHADOW — structura repo-ului

Un singur repo (monorepo). Folderele principale sunt împărțite după **ce rulează separat**, iar fiecare om lucrează
în folderul lui. Documentul are: scheletul principal, apoi scheletul complet al fiecărui serviciu, apoi ce se
schimbă odată cu `uv`.

**Legendă:** `✔` = fișierul există deja în `shadow-contract.zip` și doar se mută aici. Restul se scriu la hackathon.

## Cuprins

1. [Scheletul principal](#1-scheletul-principal)
2. [contract/](#2-contract)
3. [backend/](#3-backend)
4. [frontend/](#4-frontend)
5. [ai/](#5-ai)
6. [security/](#6-security)
7. [data/](#7-data)
8. [docs/ și scripts/](#8-docs-și-scripts)
9. [Fișierele din rădăcină](#9-fișierele-din-rădăcină)
10. [uv: ce schimbă și ce nu](#10-uv-ce-schimbă-și-ce-nu)
11. [Unde ajung fișierele din shadow-contract.zip](#11-unde-ajung-fișierele-din-shadow-contractzip)
12. [Reguli de lucru](#12-reguli-de-lucru)
13. [Cum creezi scheletul](#13-cum-creezi-scheletul)

---

## 1. Scheletul principal

```
shadow/
├── README.md              cum pornești tot + cine lucrează unde
├── docker-compose.yml     pornește backend, frontend, ai și modelul cu o comandă
├── .env.example           variabilele de mediu, fără valori secrete
├── .gitignore
│
├── contract/              contractul API (generat): openapi + documentația
├── backend/               API-ul FastAPI, cu uv
├── frontend/              interfața Next.js
├── ai/                    medicul AI, serviciu separat
├── security/              ce NU rulează în aplicație: amenințări, arhitectură, audit, chei
├── data/                  datele comune: praguri, catalog, texte, DONKI, scenariu
├── docs/                  plan, pitch, research, design
└── scripts/               generatorul de documentație, teste de contract, pornire și reset de demo
```

### Cine lucrează unde

| Cine | Folderul lui | Mai atinge |
|---|---|---|
| Frontend (2) | `frontend/` | nimic |
| Backend (2) | `backend/app/routers`, `engine`, `simulator`, `link`, `db` | `data/`; `contract/` doar prin generator |
| Securitate (2) | `backend/app/security/` și `security/` | `backend/app/link/` (sigilarea pachetelor), `backend/app/deps.py` |
| AI | `ai/` | `backend/app/routers/ai.py` (un singur fișier) |
| Toți | `docs/` | |

### De ce așa

- **Securitatea are două locuri.** Codul ei (parole, tokenuri, semnături, criptare, jurnal) rulează în același
  proces cu API-ul, deci stă în `backend/app/security/`. Folderul de sus `security/` ține doar ce nu intră în
  aplicație. Un pachet separat ar complica importurile și Docker-ul, fără niciun câștig la 24 de ore.
- **AI-ul e serviciu separat.** Are propriul proces, dependențe grele și propriul Dockerfile. Dacă pică, restul
  aplicației merge, iar `/ai/chat` întoarce textul din catalog.
- **`data/` e separat de cod.** Pragurile și catalogul sunt citite și de backend, și de AI, și se pot corecta fără
  să atingi cod.

---

## 2. contract/

Toate contractele dintre părțile aplicației. Fiecare are o sursă de adevăr în cod; documentația se generează din ea
cu `scripts/build_docs.py`. Se editează doar `guide.md` și `contract/README.md`.

```
contract/
├── README.md              cuprinsul contractelor (scris de mână)
├── api/                   frontend ↔ backend      (sursa: backend/app/schemas.py + routerele)
│   ├── guide.md           partea scrisă de mână
│   ├── README.md          generat: ghid + referința endpoint-urilor + modelele
│   └── openapi.yaml/json  generate; din openapi.json se generează tipurile TypeScript
├── ai/                    backend ↔ serviciul AI   (sursa: ai/service/schemas.py)
│   ├── guide.md, README.md, openapi.yaml/json
├── security/              backend ↔ securitate     (sursa: semnăturile din backend/app/security/)
│   ├── guide.md, README.md
└── data/                  backend ↔ data/          (sursa: backend/app/datafiles.py)
    ├── guide.md, README.md
    └── schemas/*.schema.json
```

## 3. backend/

API-ul. Un singur proces FastAPI, bază de date SQLite, gestionat cu `uv`.

```
backend/
├── README.md
├── pyproject.toml             dependențele (uv); înlocuiește requirements.txt
├── uv.lock                    versiunile exacte; SE COMITE în git
├── .python-version            3.12
├── Dockerfile
│
├── app/
│   ├── __init__.py          ✔
│   ├── main.py              ✔ aplicația, forma unică a erorilor, OpenAPI
│   ├── schemas.py           ✔ SURSA DE ADEVĂR: toate modelele contractului API
│   ├── ai_schemas.py        ✔ contractul cu serviciul AI (copie a ai/service/schemas.py)
│   ├── datafiles.py         ✔ formatul fișierelor din data/ + load_all()
│   ├── deps.py              ✔ current_user, require_roles, crew_access, difuzorul SSE
│   ├── examples.py          ✔ datele mock; dispare pe măsură ce apare logica reală
│   ├── config.py              setările citite din .env
│   ├── clock.py               SimClock: singura sursă de timp din aplicație
│   │
│   ├── routers/               endpoint-urile, câte un fișier pe domeniu          [backend]
│   │   ├── auth.py          ✔ conturi, login, logout
│   │   ├── mission.py       ✔ starea misiunii, mediul, ceasul
│   │   ├── crew.py          ✔ tabloul de bord, panoul pilonului, serii, derulator
│   │   ├── checkin.py       ✔ check-in-ul de dimineață
│   │   ├── behavioral.py    ✔ tastare și test de reacție
│   │   ├── exercise.py      ✔ exerciții
│   │   ├── alerts.py        ✔ alerte, escaladare, catalog
│   │   ├── link.py          ✔ coada de pachete, răspunsul Pământului
│   │   ├── radiation.py     ✔ dozimetrul, adăpostul
│   │   ├── ai.py            ✔ apelează serviciul din ai/                          [AI]
│   │   ├── security.py      ✔ jurnal, respingeri, primirea măsurătorilor, dovezi
│   │   ├── demo.py          ✔ butoanele de demo și resetul
│   │   └── events.py        ✔ fluxul SSE
│   │
│   ├── db/                    baza de date                                        [backend]
│   │   ├── session.py         conexiunea SQLite (SQLAlchemy)
│   │   ├── models.py          tabelele: users, checkins, measurements, alerts, packets, access_log…
│   │   └── seed.py            încarcă seed/users.json și scenariul la pornire
│   │
│   ├── engine/                motorul de baseline și triaj: funcții pure, fără HTTP  [backend]
│   │   ├── baseline.py        normalul personal al fiecărui astronaut
│   │   ├── triage.py          praguri → nivel 1/2/3, crearea alertelor, reverificarea
│   │   ├── perception_gap.py  decalajul dintre check-in și datele obiective
│   │   ├── cross_signals.py   semnale încrucișate; cauză individuală sau de mediu
│   │   ├── radiation.py       detectorul: 2× media pe 24 h, 3 citiri
│   │   └── pillars/
│   │       ├── behavioral.py      trăsăturile tastării, PVT
│   │       ├── cardio.py          scorul de pregătire pentru revenire
│   │       ├── immune.py          NightSignal, indicele de stres
│   │       └── musculoskeletal.py scorul de încărcare, recomandarea de împărțire
│   │
│   ├── simulator/             datele simulate                                     [backend]
│   │   ├── scenario.py        generatorul celor 140 de zile, pe fiecare membru
│   │   ├── radiation.py       curba dozei și redarea evenimentului DONKI
│   │   └── devices.py         dispozitivele simulate care trimit măsurători semnate
│   │
│   ├── link/                  coada navă ↔ Pământ                                 [backend + securitate]
│   │   ├── queue.py           pachetele și stările lor
│   │   ├── scheduler.py       task-ul care trimite și livrează, la 1 secundă
│   │   └── windows.py         ferestrele de comunicare și întârzierea pe mediu
│   │
│   └── security/              codul de securitate din aplicație                   [securitate]
│       ├── passwords.py       hash și verificare (argon2 / bcrypt)
│       ├── tokens.py          JWT: emitere, verificare, lista de tokenuri revocate
│       ├── lockout.py         blocarea contului după 5 parole greșite
│       ├── keys.py            încărcarea cheilor din .env / fișiere
│       ├── signing.py         Ed25519: semnare și verificare (măsurători, pachete)
│       ├── sealing.py         seal(payload) / open(packet): AES-256-GCM + semnătură + replay
│       ├── validation.py      valori imposibile, senzor înghețat
│       └── access_log.py      jurnalul cu hash înlănțuit
│
├── tests/                     pytest; rezultatul apare în ecranul Evidence
│   ├── conftest.py
│   ├── routers/               fiecare endpoint răspunde conform contractului
│   ├── engine/                pragurile și triajul
│   ├── link/                  coada, întârzierea
│   └── security/              semnături, pachet falsificat, conturi separate
│
└── seed/
    └── users.json           ✔ conturile de test: câte unul pe astronaut
```

**Granița backend ↔ securitate** e în două locuri, stabilite din prima oră:

| Fișier | Funcțiile | Cine le scrie | Cine le apelează |
|---|---|---|---|
| `security/sealing.py` | `seal(payload, header) -> bytes`, `open(blob, header) -> payload` (aruncă dacă semnătura e invalidă) | securitate | `link/scheduler.py` |
| `security/tokens.py` | `issue(user) -> str`, `decode(token) -> claims` | securitate | `deps.py`, `routers/auth.py` |

---

## 4. frontend/

Next.js (App Router) + Tailwind. Vorbește cu backend-ul **doar** prin `src/lib/api.ts`.

```
frontend/
├── README.md
├── package.json
├── tsconfig.json
├── next.config.ts
├── .env.local.example             NEXT_PUBLIC_API_URL=http://localhost:8000
├── Dockerfile
│
├── public/
│   ├── body/                      ilustrația corpului (licență liberă) + sursa ei
│   └── fonts/                     Geist, Geist Mono (local, pentru modul offline)
│
└── src/
    ├── app/
    │   ├── layout.tsx             fonturi, tema, furnizorii de autentificare și evenimente
    │   ├── globals.css
    │   ├── page.tsx               trimite la /login sau la ecranul rolului
    │   ├── login/                 ecranul „Cine ești?”: casete pe astronaut + parolă
    │   ├── (ship)/                tot ce e la bord (rolurile astronaut și cmo)
    │   │   ├── layout.tsx         antet: cine e autentificat, ceasul misiunii, comutatorul de mediu
    │   │   ├── dashboard/         corpul interactiv, panoul zonei, decalajul de percepție
    │   │   ├── checkin/           check-in-ul de dimineață
    │   │   ├── pvt/               testul de reacție de 3 minute
    │   │   ├── alerts/[id]/       alerta completă, planul, escaladarea
    │   │   ├── cmo/               coada ofițerului medical
    │   │   └── evidence/          teste, praguri cu surse, jurnal, respingeri
    │   └── mission-control/       ecranul Pământului (rolul earth)
    │
    ├── components/
    │   ├── body/                  BodyMap, ZonePanel
    │   ├── charts/                graficul cu banda de baseline, curba dozei
    │   ├── checkin/               câmpurile, mesajele de respingere
    │   ├── keystrokes/            barele live, comparația ora 2 / ora 18
    │   ├── alerts/                banner, planul cu bife, istoricul
    │   ├── link/                  bara de progres a pachetului, coada, formularul de răspuns
    │   ├── radiation/             banner-ul „Mergi în adăpost”, minutele câștigate
    │   ├── ai/                    cardul medicului AI, sursele citate
    │   ├── layout/                antetul, derulatorul misiunii, comutatorul de mediu
    │   └── ui/                    butoane, etichete de stare (culoare + formă + cuvânt)
    │
    ├── lib/
    │   ├── api.ts               ✔ clientul tipizat, login/logout, SSE, colectorul de tastare
    │   ├── shadow-api.d.ts      ✔ tipurile generate din contract (nu se editează)
    │   ├── auth.tsx               contextul de autentificare; golește tot la schimbarea astronautului
    │   ├── events.tsx             furnizorul SSE
    │   └── format.ts              date, unități, timp de misiune
    │
    ├── hooks/                     useDashboard, usePillar, useMission…
    └── styles/                    tokens.css: culorile și spațierile din mockup
```

Împărțirea între cei doi de pe frontend, ca să nu se calce: unul ia `(ship)/dashboard`, `components/body`,
`charts`, `keystrokes`, `ai`; celălalt ia `login`, `checkin`, `pvt`, `alerts`, `cmo`, `evidence`,
`mission-control`, `link`, `radiation`. `lib/` și `components/ui` sunt comune: se anunță înainte de schimbări.

---

## 5. ai/

Serviciu propriu, pe portul **8001**. Backend-ul e singurul lui client.

```
ai/
├── README.md
├── pyproject.toml             proiect uv propriu, separat de backend
├── uv.lock
├── Dockerfile
│
├── service/
│   ├── main.py                FastAPI: POST /chat, GET /status
│   ├── schemas.py             cererea și răspunsul serviciului
│   └── llm.py                 clientul către llama-server (limită de timp, reîncercare)
│
├── rag/
│   ├── ingest.py              corpus/ → bucăți → index/
│   ├── retrieve.py            întrebare → fragmentele relevante, cu titlu și URL
│   └── embed.py               modelul de embedding, rulat local
│
├── prompts/
│   ├── system.md              rolul: reformulează catalogul, citează, nu decide triajul
│   └── answer.md              șablonul răspunsului
│
├── corpus/                    documentele NASA / CSA, ca text
│   └── sources.json           titlu + URL pentru fiecare document (de aici vin citările)
│
├── index/                     indexul RAG (generat, NU intră în git)
├── models/                    fișierele GGUF (NU intră în git) + README cu numele modelului
├── eval/
│   ├── questions.json         întrebări de test cu răspunsul așteptat
│   └── run_eval.py
└── finetune/                  bonus opțional: scripturile LoRA
```

**Contractul intern backend → ai** (singurul punct de legătură):

| | |
|---|---|
| Cerere | `POST http://ai:8001/chat` cu `{ message, history, context }`, unde `context` conține alerta, dovezile și recomandarea din catalog, adăugate de backend |
| Răspuns | `{ answer, citations: [{title, url, snippet}], recommendation_ids, model, latency_ms }` |
| Limită | backend-ul așteaptă 20 de secunde; apoi întoarce textul din catalog, cu `fallback = true` |
| Stare | `GET http://ai:8001/status` → `{ ready, model, mode }` |

---

## 6. security/

Tot ce ține de securitate și **nu** rulează în aplicație.

```
security/
├── README.md
├── threat-model.md            ce apărăm, de cine, ce atacuri contează (urgență ascunsă, alarmă falsă)
├── architecture.md            chei, semnături, criptare, roluri, jurnal: cum se leagă
├── checklist.md               fiecare cerință, cu starea ei: făcut, parțial, nefăcut
│
├── keys/
│   ├── README.md
│   └── generate_keys.py       generează cheile Ed25519 și cheia AES (cheile NU intră în git)
│
└── audit/
    ├── findings.md            ce s-a găsit la audit, ce s-a reparat, ce a rămas deschis
    └── check_endpoints.py     401 fără token, 403 pentru alt astronaut, pe aplicația reală
```

Scripturi de atac nu există: atacurile se arată din panoul *Demo* al aplicației și sunt acoperite de teste
(`security/checklist.md`).

---

## 7. data/

Fără cod. Citit de backend și de AI.

```
data/
├── README.md
├── parameters.json            pragurile, fiecare cu sursa lui (din research)
├── environments.json          cele 4 medii: întârziere, gravitație, doză de fond
│
├── catalog/
│   ├── recommendations.json   catalogul folosit de triaj (id, nivel, declanșator, acțiune, sursă)
│   └── catalog_recomandari_texte.md   varianta de citit, din research
│
├── texts/
│   ├── checkin_indicators.json    „cum se măsoară”, „ce înseamnă”, „de ce contează în spațiu”
│   └── body_functions.json        funcția fiecărei părți a corpului + pericolul spațial
│
├── donki/
│   └── donki_sep_event.json   evenimentul solar real din 11 mai 2024
│
└── scenario/
    └── scenario.json          ce se întâmplă în fiecare zi a misiunii simulate, pe fiecare membru
```

---

## 8. docs/ și scripts/

```
docs/
├── README.md
├── STRUCTURA_REPO.md          acest document
├── plan/                      planul final (PDF)
├── pitch/                     prezentarea, textul de 4 minute
├── research/                  rezultatele de research, cu sursele
├── design/                    filosofia vizuală, capturi din mockup
└── demo/                      scenariul de demo pas cu pas, video de rezervă (link, nu fișierul)

scripts/
├── README.md
├── build_docs.py            ✔ regenerează tot contract/ (api, ai, security, data)
├── validate_data.py         ✔ verifică fișierele din data/
├── smoke.py                 ✔ apelează toate endpoint-urile și verifică permisiunile
├── request_examples.py      ✔ o cerere de exemplu pentru fiecare endpoint
├── gen_types.sh             ✔ contract/api/openapi.json → frontend/src/lib/shadow-api.d.ts
├── dev.sh                     pornește tot local, fără Docker
└── demo_reset.sh              readuce demo-ul la starea inițială
```

---

## 9. Fișierele din rădăcină

| Fișier | Ce conține |
|---|---|
| `README.md` | ce e proiectul, cum pornești tot în 3 comenzi, tabelul „cine lucrează unde”, linkuri spre `contract/README.md` și `docs/` |
| `docker-compose.yml` | patru servicii: `backend` (8000), `frontend` (3000), `ai` (8001), `llama` (8080); `data/` montat doar pentru citire în `backend` și `ai`; imaginile sunt descărcate dinainte, pentru modul offline |
| `.env.example` | `JWT_SECRET`, `LINK_AES_KEY_B64`, `TIME_SCALE`, `DATABASE_URL`, `DATA_DIR`, `AI_URL`, `LLAMA_URL`, `NEXT_PUBLIC_API_URL` |
| `.gitignore` | `.env`, cheile, `.venv/`, `node_modules/`, `.next/`, baza SQLite, `ai/models/*`, `ai/index/*` |

---

## 10. uv: ce schimbă și ce nu

**Nu afectează** frontend-ul, contractul, datele sau documentele. `uv` e doar felul în care backend-ul își
instalează pachetele Python. Schimbă cinci lucruri mici:

**1. Fișierele din `backend/`.** `requirements.txt` dispare; apar `pyproject.toml`, `uv.lock` și
`.python-version`. `uv.lock` **se comite**, ca toți să aibă aceleași versiuni.

Scheletul vine deja cu `pyproject.toml`, `uv.lock` și `.python-version`; prima comandă e `uv sync`.

**2. Comenzile zilnice.**

| În loc de | Cu uv |
|---|---|
| `pip install -r requirements.txt` | `uv sync` |
| `pip install <pachet>` | `uv add <pachet>` (scrie singur în `pyproject.toml` și `uv.lock`) |
| `uvicorn app.main:app --reload` | `uv run uvicorn app.main:app --reload --port 8000` |
| `pytest` | `uv run pytest` |

Nu faceți `pip install` de mână în `.venv`: pachetul nu ajunge în `uv.lock` și la colegi nu va merge.

**3. Scripturile din `scripts/` și `security/`** importă codul backend-ului, deci se rulează cu mediul lui,
din rădăcina repo-ului:

```bash
uv run --project backend python scripts/smoke.py
uv run --project backend python scripts/build_docs.py
uv run --project backend python security/audit/check_endpoints.py
```

**4. Dockerfile-ul backend-ului** folosește uv:

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app ./app
COPY seed ./seed
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Construiți imaginea **înainte** de demo: `uv sync` are nevoie de internet, iar demo-ul rulează offline.

**5. `ai/` e proiect uv separat**, cu propriul `pyproject.toml` și `uv.lock`. Nu le uniți: AI-ul are dependențe
grele (embedding, index) de care backend-ul nu are nevoie, iar așa fiecare se instalează repede.

Cine are nevoie de `uv` instalat: cei de pe backend, securitate și AI. Cei de pe frontend, doar dacă vor să
pornească backend-ul local fără Docker.

---

## 11. Unde ajung fișierele din shadow-contract.zip

Începând cu versiunea 1.2, zip-ul are **exact structura repo-ului**: se dezarhivează în rădăcina repo-ului clonat
și nu mai trebuie mutat nimic. Conține scheletul de foldere, contractele, mock-ul backend-ului, mock-ul serviciului
AI, modulele provizorii de securitate, fișierele din `data/`, clientul frontend-ului, scripturile și documentele
echipelor (în `docs/`).

## 12. Reguli de lucru

1. **Fiecare în folderul lui.** Dacă trebuie să schimbi ceva în folderul altcuiva, îi spui întâi.
2. **Contractul se schimbă într-un singur fel:** `backend/app/schemas.py` → `scripts/build_docs.py` →
   `scripts/gen_types.sh` → un commit care începe cu `contract:`.
3. **Commit-uri mici și dese**, cu prefix după folder: `backend:`, `frontend:`, `ai:`, `security:`, `data:`,
   `docs:`, `contract:`. Înainte de `push`: `git pull --rebase`.
4. **Nu intră niciodată în git:** `.env`, chei, modele GGUF, baza SQLite, `.venv/`, `node_modules/`.
5. **Ce se rupe pe `main` se repară imediat** sau se dă înapoi. La ora 10 e prima integrare cap-coadă.

---

## 13. Cum creezi scheletul

Git nu păstrează foldere goale, deci fiecare folder primește un `README.md` scurt (ce intră aici, cine lucrează)
sau un `.gitkeep`.

**Cu scriptul** (`create_skeleton.sh`, livrat lângă acest document). Creează doar foldere, README-uri,
`.gitkeep`, `.gitignore` și `.env.example`; nu suprascrie nimic existent:

```bash
git clone <adresa-repo> shadow && cd shadow
bash create_skeleton.sh
git add -A && git commit -m "chore: scheletul repo-ului" && git push
```

**De mână, pe GitHub:** „Add file → Create new file” și scrii calea completă, de exemplu
`backend/app/security/README.md`. Folderele se creează singure.
