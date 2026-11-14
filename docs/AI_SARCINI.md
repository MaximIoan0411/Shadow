# AI — ce trebuie implementat

**Folder:** `ai/` · **Unelte:** Python 3.12, uv (proiect separat de backend), FastAPI, llama.cpp (`llama-server`)

Medicul AI de bord: un model mic, care rulează local, fără internet, și care **explică** o recomandare în cuvinte
simple, cu surse NASA citate. Nu pune diagnostice și nu decide nivelul unei alerte: triajul și catalogul sunt ale
backend-ului și merg și fără AI.

**Cum se leagă:** serviciul rulează pe portul **8001**. Singurul lui client este backend-ul, care îl apelează din
`/ai/chat`. Frontend-ul nu vorbește niciodată direct cu el.

**Priorități:** `P0` = fără el nu există medicul AI în demo · `P1` = dacă e gata până la ora 16 · `P2` = bonus.

## Cuprins

1. [Modelul local](#1-modelul-local-p0)
2. [Corpusul de documente](#2-corpusul-de-documente-p0)
3. [Indexarea](#3-indexarea-p0)
4. [Căutarea](#4-căutarea-p0)
5. [Promptul](#5-promptul-p0)
6. [Serviciul](#6-serviciul-p0)
7. [Limitele răspunsului](#7-limitele-răspunsului-p0)
8. [Viteza](#8-viteza-p1)
9. [Evaluarea](#9-evaluarea-p1)
10. [Planul B](#10-planul-b)
11. [Bonus: fine-tuning](#11-bonus-fine-tuning-p2)
12. [Ordinea de lucru](#12-ordinea-de-lucru)
13. [Cu cine te legi](#13-cu-cine-te-legi)
14. [Scheletul gol](#14-scheletul-gol)

---

## 1. Modelul local (P0)

- **Ce face:** un model open-source de 3–4 miliarde de parametri, în format GGUF, cuantizat Q4 (aproximativ 2–3 GB
  de memorie), servit de `llama-server` pe portul 8080.
- **Reguli:**
  - fișierul modelului stă în `ai/models/` și **nu intră în git**; numele exact și locul de descărcare se scriu
    în `ai/models/README.md`;
  - modelul trebuie să răspundă bine în **română**: verificați asta înainte de orice altceva;
  - se descarcă înainte de demo; în demo nu există internet.
- **Țintă:** primul cuvânt în cel mult 2 secunde, răspuns complet în cel mult 15 secunde, pe laptopul de demo.
- **Gata când:** `llama-server` pornește cu Wi-Fi-ul oprit și răspunde în română la o întrebare simplă.

## 2. Corpusul de documente (P0)

`ai/corpus/`.

- **Ce face:** adună textele din care modelul are voie să citeze.
- **Ce intră:**
  - resursele oficiale ale challenge-ului: paginile NASA HRP „5 Hazards of Human Spaceflight” și „Risks of Human
    Spaceflight”, „Ongoing HRP Research”, paginile CSA;
  - paginile NASA ale riscurilor folosite în catalog (somn, comportament, cardiovascular, imunitar, oase, radiații);
  - fragmentele relevante din rapoartele de dovezi NASA citate în `data/parameters.json`;
  - catalogul echipei: `data/catalog/recommendations.json`.
- **Reguli:**
  - fiecare document e un fișier text, iar `corpus/sources.json` îi dă titlul și URL-ul (de aici vin citările);
  - doar surse care apar deja în `parameters.json` sau în resursele oficiale; nimic adăugat din memorie;
  - păstrați textul original, în engleză; modelul răspunde în română.
- **Gata când:** fiecare fișier din `corpus/` are o intrare în `sources.json`, cu URL care se deschide.

## 3. Indexarea (P0)

`ai/rag/ingest.py`, `ai/rag/embed.py`.

- **Ce face:** taie documentele în fragmente de 150–300 de cuvinte, cu puțină suprapunere, calculează un vector
  pentru fiecare și salvează totul în `ai/index/`.
- **Reguli:**
  - model de embedding **multilingv** și mic, rulat local: întrebările vin în română, iar documentele sunt în engleză;
  - fiecare fragment își păstrează titlul, URL-ul și poziția în document;
  - indexul se reface cu o singură comandă și nu intră în git;
  - la câteva sute de fragmente ajunge o căutare simplă prin similaritate; nu e nevoie de o bază de date de vectori.
- **Gata când:** `uv run python -m rag.ingest` reface indexul fără internet.

## 4. Căutarea (P0)

`ai/rag/retrieve.py`.

- **Ce face:** pentru o întrebare, întoarce cele mai relevante 3–4 fragmente, cu titlu, URL și text.
- **Reguli:**
  - în căutare intră întrebarea **și** subiectul alertei primit de la backend (de exemplu „imunitar, puls de
    noapte”), ca să aducă fragmentele potrivite;
  - sub un prag de similaritate nu se întoarce nimic: mai bine „fără sursă” decât o sursă nepotrivită.
- **Gata când:** întrebarea „De ce mi-a crescut pulsul de noapte?” aduce fragmente despre sistemul imunitar, nu
  despre oase.

## 5. Promptul (P0)

`ai/prompts/system.md`, `ai/prompts/answer.md`.

- **Ce primește modelul:** rolul, recomandarea din catalog (de la backend), dovezile alertei, fragmentele găsite
  și întrebarea.
- **Ce trebuie să facă:**
  - să răspundă în română, scurt (3–5 propoziții), pe înțelesul unui om care nu e medic;
  - să **reformuleze recomandarea din catalog**, nu să inventeze alta;
  - să folosească doar informația din fragmentele primite;
  - să spună clar când trebuie anunțat ofițerul medical.
- **Ce nu are voie:**
  - să pună un diagnostic sau să numească un medicament ori o doză;
  - să schimbe nivelul alertei;
  - să dea cifre care nu apar în context.
- **Gata când:** zece întrebări diferite primesc răspunsuri care respectă toate regulile de mai sus.

## 6. Serviciul (P0)

`ai/service/main.py`, `schemas.py`, `llm.py`.

Contractul complet (modele, erori, exemple reale) e în `contract/ai/README.md`, iar modelele în
`ai/service/schemas.py`, cu o copie identică în `backend/app/ai_schemas.py`. **Serviciul există deja ca mock**
(`uv run uvicorn service.main:app --port 8001`); înlocuiți corpul funcțiilor, nu semnăturile.

**`POST /chat`**

```json
{
  "message": "De ce mi-a crescut pulsul de noapte?",
  "history": [],
  "context": {
    "topic": "immune",
    "level": 2,
    "alert_title": "Puls de noapte +7 bpm, 3 nopți la rând",
    "evidence": [ { "label": "Puls de noapte", "value": 61, "unit": "bpm", "deviation_text": "+7 bpm peste mediana personală, 3 nopți" } ],
    "recommendation": {
      "id": "immune-2-1", "level": 2,
      "trigger": "Puls mediu de noapte ≥ +4 bpm peste mediana personală, două nopți la rând.",
      "action": "Anunță ofițerul medical de la bord…",
      "source_citation": "Alavi et al. (2022), Nature Medicine 28:175–184",
      "source_url": "https://www.nature.com/articles/s41591-021-01593-2"
    },
    "mission_day": 96,
    "environment": "mars_transit"
  }
}
```

Răspuns:

```json
{
  "answer": "Pulsul tău de noapte e cu 7 bpm peste normalul tău de trei nopți…",
  "citations": [ { "title": "Alavi et al. (2022), Nature Medicine", "url": "https://…", "snippet": "…" } ],
  "recommendation_ids": ["immune-2-1"],
  "off_topic": false,
  "model": "numele-modelului-Q4_K_M",
  "latency_ms": 2140
}
```

**`GET /status`** → `{ "ready": true, "model": "…", "mode": "local", "corpus_documents": 42 }`
(`mode` ∈ `local`, `colab_simulation`, `mock`). Modelul nu răspunde → `503` cu `{"error": {"code": "model_unavailable", …}}`.

- **Reguli:**
  - `context` vine întotdeauna de la backend, **fără nume și fără `crew_id`**; serviciul nu citește baza de date și nu primește alte date medicale;
  - `citations` conține doar fragmentele folosite efectiv în răspuns;
  - `mode` spune onest unde rulează modelul: `local` sau `colab_simulation`;
  - dacă `llama-server` nu răspunde, serviciul întoarce repede `503 model_unavailable`; **fallback-ul pe catalog îl face backend-ul**;
  - întrebare în afara subiectului → `off_topic = true`, cu mesajul fix, fără citări.
- **Gata când:** `curl` pe `/chat` întoarce un răspuns cu cel puțin o citare.

## 7. Limitele răspunsului (P0)

Verificări făcute în cod, după ce modelul a răspuns, nu doar cerute în prompt:

- dacă nu s-a găsit niciun fragment → `citations` gol, iar răspunsul e doar reformularea recomandării din catalog;
- dacă întrebarea e în afara subiectului (nu ține de sănătatea în misiune) → un răspuns scurt, fix: „Pot ajuta
  doar cu întrebări despre sănătatea ta în misiune”;
- răspunsul se taie la o lungime maximă;
- mențiunea „Prototip de sprijin, nu dispozitiv medical” o adaugă backend-ul, nu modelul.

## 8. Viteza (P1)

- Modelul se încarcă la pornirea serviciului, nu la prima întrebare.
- Un apel de încălzire la pornire, ca prima întrebare din demo să nu fie cea lentă.
- Context scurt: 3–4 fragmente, nu zece.
- Măsurați pe **laptopul de demo**, nu pe placa video de pe Colab.
- **Gata când:** trei întrebări la rând răspund sub 15 secunde fiecare, cu Wi-Fi-ul oprit.

## 9. Evaluarea (P1)

`ai/eval/questions.json`, `ai/eval/run_eval.py`.

- 10–15 întrebări, cel puțin două pe fiecare pilon, plus două în afara subiectului.
- Pentru fiecare: are citare? citarea e din subiectul corect? respectă interdicțiile (fără diagnostic, fără
  medicamente)? e în română?
- Rezultatul, un tabel scurt, se pune în `docs/` și se poate arăta juriului.
- **Gata când:** rulezi evaluarea cu o comandă și știi câte întrebări trec.

## 10. Planul B

În această ordine, dacă ceva nu merge:

1. **Modelul e prea lent pe laptop** → un model mai mic sau o cuantizare mai agresivă.
2. **Tot prea lent** → modelul rulează pe Colab, iar în interfață apare deschis „simulare a calculatorului de
   bord” (`mode = "colab_simulation"`).
3. **Nimic nu merge** → serviciul rămâne oprit, iar aplicația afișează textul din catalog. Demo-ul nu depinde de AI.

Decizia se ia la **ora 12**, nu mai târziu.

## 11. Bonus: fine-tuning (P2)

`ai/finetune/`. Doar dacă totul de mai sus e gata și regulamentul permite.

- LoRA pe placa RTX Pro 6000 din Colab, pe perechi întrebare–răspuns construite din catalog și din corpus.
- Modelul rezultat se cuantizează și se încarcă la fel ca cel de bază.
- Se păstrează modelul de bază ca rezervă: dacă varianta antrenată răspunde mai prost la evaluare, nu se folosește.

---

## 12. Ordinea de lucru

| Ore | Ce |
|---|---|
| 0–2 | modelul pornit local, verificat în română; forma cererii și a răspunsului stabilită cu backend-ul |
| 2–6 | corpusul adunat, indexarea, căutarea |
| 6–10 | promptul, serviciul `/chat` și `/status` |
| 10 | prima integrare: backend-ul apelează serviciul |
| 12 | **decizia: local, Colab sau doar catalog** |
| 12–16 | limitele răspunsului, viteza, evaluarea |
| 16–18 | bonus, dacă e timp |
| 18–24 | repetiții cu Wi-Fi-ul oprit |

## 13. Cu cine te legi

| Cu cine | Ce | Unde | Când se stabilește |
|---|---|---|---|
| **Backend** | forma cererii și a răspunsului pentru `/chat` și `/status`; limita de 20 de secunde; cine face fallback-ul (backend-ul) | `ai/service/schemas.py` ↔ `backend/app/routers/ai.py` | ora 0–1 |
| **Data** | catalogul și sursele din `parameters.json`, din care se construiește corpusul | `data/catalog/`, `data/parameters.json` | ora 0–2 |
| **Securitate** | serviciul ascultă doar în rețeaua internă (nu e expus în afară); nu primește date medicale în afara câmpului `context` | `docker-compose.yml` | ora 2–6 |
| **Frontend** | nimic direct | — | — |

## 14. Scheletul gol

```
ai/
├── README.md
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── service/
│   ├── main.py
│   ├── schemas.py
│   └── llm.py
├── rag/
│   ├── ingest.py
│   ├── embed.py
│   └── retrieve.py
├── prompts/
│   ├── system.md
│   └── answer.md
├── corpus/
│   └── sources.json
├── index/            (generat; nu intră în git)
├── models/           (GGUF; nu intră în git)
│   └── README.md
├── eval/
│   ├── questions.json
│   └── run_eval.py
└── finetune/
```
