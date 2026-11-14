# SHADOW — contractul backend ↔ serviciul AI

**Versiunea 1.2.0** · serviciul ascultă pe portul **8001** · singurul lui client: **backend-ul**

Medicul AI rulează ca serviciu separat, în `ai/`. Backend-ul îl apelează din `POST /api/v1/ai/chat` (contractul cu
frontend-ul: `contract/api/README.md`). Frontend-ul nu-l apelează niciodată direct.

```
frontend ──POST /api/v1/ai/chat──► backend ──POST http://ai:8001/chat──► serviciul AI ──► llama-server (8080)
                                     │  construiește contextul               │  RAG peste ai/corpus/
                                     │  limită 20 s, fallback pe catalog      │  prompt din ai/prompts/
```

## Cuprins

1. [Pornire](#1-pornire)
2. [Regulile](#2-regulile)
3. [Ce trimite backend-ul](#3-ce-trimite-backend-ul)
4. [Ce face backend-ul cu răspunsul](#4-ce-face-backend-ul-cu-răspunsul)
5. [Erori și limite de timp](#5-erori-și-limite-de-timp)
6. [Cum schimbăm contractul](#6-cum-schimbăm-contractul)
7. [Referința endpoint-urilor](#7-referința-endpoint-urilor)
8. [Modelele](#8-modelele)

---

## 1. Pornire

Serviciul există deja ca **mock**: răspunde după contract, fără model. Reformulează direct recomandarea din
context și citează sursa ei. Backend-ul își poate scrie puntea pe el din primul minut.

```bash
cd ai
uv sync
uv run uvicorn service.main:app --reload --port 8001
# http://localhost:8001/docs
```

Backend-ul îl găsește la `AI_URL` (implicit `http://localhost:8001`; în Docker Compose `http://ai:8001`).

## 2. Regulile

1. **Doar backend-ul îl apelează.** În Docker Compose serviciul nu are port expus în afară.
2. **Contextul îl construiește backend-ul**: alerta, dovezile și recomandarea din catalog. Serviciul nu citește
   baza de date și nu primește alte date medicale.
3. **Fără identitate:** contextul nu conține nume și nici `crew_id`. Serviciul nu are nevoie să știe cine întreabă.
4. **Serviciul reformulează recomandarea din catalog** și citează surse din `ai/corpus/`. Nu pune diagnostice, nu
   numește medicamente sau doze, nu schimbă nivelul alertei.
5. **Fallback-ul îl face backend-ul.** Serviciul doar răspunde repede cu o eroare dacă modelul nu e disponibil.
6. **`citations` conține doar fragmentele folosite efectiv.** O listă goală înseamnă „fără sursă” și apare așa în
   interfață.

## 3. Ce trimite backend-ul

Din cererea frontend-ului (`AiChatRequest`: `crew_id`, `message`, `alert_id`, `history`), backend-ul construiește
`AiServiceChatRequest`:

| Câmp trimis serviciului | De unde îl ia backend-ul |
|---|---|
| `message` | `message` din cererea frontend-ului |
| `history` | ultimele max. 6 mesaje din `history` |
| `context.topic`, `context.level`, `context.alert_title` | alerta `alert_id` (dacă există) |
| `context.evidence` | `evidence` al alertei: eticheta, valoarea, unitatea, textul abaterii |
| `context.recommendation` | intrarea din `data/catalog/recommendations.json` a alertei: `id`, `level`, `trigger`, `action`, sursa |
| `context.mission_day`, `context.environment` | ceasul misiunii și mediul curent |

Fără `alert_id`, contextul are doar ziua și mediul; serviciul răspunde general sau marchează `off_topic`.

## 4. Ce face backend-ul cu răspunsul

`AiServiceChatResponse` → `AiChatResponse` (modelul din contractul API):

| Câmp API | Valoare |
|---|---|
| `answer` | `answer` |
| `citations` | `citations` (titlu, URL, fragment) |
| `recommendation_ids` | `recommendation_ids` |
| `model`, `latency_ms` | din răspuns (`latency_ms` măsurat de backend, cu tot cu rețeaua) |
| `fallback` | `false` |
| `disclaimer` | adăugat de backend: „Prototip de sprijin, nu dispozitiv medical.” |

Dacă `off_topic = true`, `answer` e mesajul fix al serviciului, iar `citations` e gol.

`GET /api/v1/ai/status` din contractul API întoarce starea din `GET /status` al serviciului; dacă serviciul nu
răspunde, `ready = false` și `mode = "fallback"`.

## 5. Erori și limite de timp

| Situația | Ce primește backend-ul | Ce întoarce backend-ul frontend-ului |
|---|---|---|
| răspuns normal | `200` | răspunsul, `fallback = false` |
| modelul nu e încărcat sau `llama-server` nu răspunde | `503` cu `{"error": {"code": "model_unavailable", ...}}` | textul `action` al recomandării din catalog, `fallback = true` |
| peste **20 de secunde** fără răspuns | backend-ul anulează cererea | ca mai sus |
| serviciul oprit (conexiune refuzată) | eroare de rețea | ca mai sus |
| `422` (cerere invalidă) | e un bug în backend | ca mai sus + log de eroare |

**`/api/v1/ai/chat` nu întoarce niciodată eroare din cauza AI-ului.** Aplicația funcționează și cu serviciul oprit.

Ținte pentru echipa de AI, pe laptopul de demo: primul cuvânt în cel mult 2 secunde, răspunsul complet în cel mult
15 secunde (sub limita de 20).

## 6. Cum schimbăm contractul

Modelele stau în **două copii identice**, fiindcă `ai/` și `backend/` sunt proiecte uv separate:

- `ai/service/schemas.py` (al echipei de AI);
- `backend/app/ai_schemas.py` (copia backend-ului).

`scripts/smoke.py` compară cele două și pică la orice diferență. O schimbare se face în **ambele fișiere, în
același PR**, cu acordul backend-ului, apoi `scripts/build_docs.py` regenerează acest document.

---

## 7. Referința endpoint-urilor

Generată din `ai/service/main.py`. Exemplele sunt răspunsuri reale ale mock-ului.

- [Endpoint-uri](#endpoint-uri)

### Endpoint-uri

#### `GET /status` — Starea modelului

**Răspuns 200:** [AiServiceStatus](#aiservicestatus)

---

#### `POST /chat` — Răspuns cu surse

**Corpul cererii:** [AiServiceChatRequest](#aiservicechatrequest)

**Răspuns 200:** [AiServiceChatResponse](#aiservicechatresponse)

**Erori posibile:** 503, 422

<details><summary>Exemplu</summary>

```http
POST /chat
```

Cerere:

```json
{
  "message": "De ce mi-a crescut pulsul de noapte?",
  "history": [],
  "context": {
    "topic": "immune",
    "level": 2,
    "alert_title": "Puls de noapte +7 bpm, 3 nopți la rând",
    "mission_day": 96,
    "environment": "mars_transit",
    "evidence": [
      {
        "label": "Puls de noapte",
        "value": 61,
        "unit": "bpm",
        "deviation_text": "+7 bpm peste mediana personală, 3 nopți"
      }
    ],
    "recommendation": {
      "id": "immune-2-1",
      "level": 2,
      "trigger": "Puls mediu de noapte ≥ +4 bpm peste mediana personală, două nopți la rând.",
      "action": "Anunță ofițerul medical de la bord, cu graficul de puls și temperatură și jurnalul de simptome.",
      "source_citation": "Alavi et al. (2022), Nature Medicine 28:175–184",
      "source_url": "https://www.nature.com/articles/s41591-021-01593-2"
    }
  }
}
```

Răspuns `200`:

```json
{
  "answer": "What was observed: +7 bpm peste mediana personală, 3 nopți. What you can do now: Anunță ofițerul medical de la bord, cu graficul de puls și temperatură și jurnalul de simptome.",
  "citations": [
    {
      "title": "Alavi et al. (2022), Nature Medicine 28:175–184",
      "url": "https://www.nature.com/articles/s41591-021-01593-2",
      "snippet": "Puls mediu de noapte ≥ +4 bpm peste mediana personală, două nopți la rând."
    }
  ],
  "recommendation_ids": [
    "immune-2-1"
  ],
  "off_topic": false,
  "model": "mock",
  "latency_ms": 0
}
```

</details>

---


## 8. Modelele

### Obiecte

#### AiEvidence

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `label` | text | da |  Ex.: `"Puls de noapte"` |
| `value` | număr \| null | nu |  Ex.: `61` |
| `unit` | text | nu |  Ex.: `"bpm"` |
| `deviation_text` | text | da |  Ex.: `"+7 bpm peste mediana personală, 3 nopți"` |

#### AiRecommendation

Intrarea din catalog pe care răspunsul trebuie s-o reformuleze.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da |  Ex.: `"immune-2-1"` |
| `level` | `1` \| `2` \| `3` | da |  |
| `trigger` | text | da |  |
| `action` | text | da |  |
| `source_citation` | text | da |  |
| `source_url` | text | da |  |

#### AiContext

Construit de backend. Fără nume, fără crew_id: serviciul nu are nevoie să știe cine întreabă.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `topic` | `"behavioral"` \| `"cardio"` \| `"immune"` \| `"musculoskeletal"` \| `"radiation"` \| `"cross_signal"` \| null | nu | Subiectul alertei. `null` = întrebare generală. |
| `level` | `1` \| `2` \| `3` \| null | nu |  |
| `alert_title` | text \| null | nu |  Ex.: `"Puls de noapte +7 bpm, 3 nopți la rând"` |
| `evidence` | listă de [AiEvidence](#aievidence) | nu |  |
| `recommendation` | [AiRecommendation](#airecommendation) \| null | nu |  |
| `mission_day` | număr întreg | da |  Ex.: `96` |
| `environment` | text | da |  Ex.: `"mars_transit"` |

#### AiTurn

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `role` | `"user"` \| `"assistant"` | da |  |
| `content` | text | da |  (lungime max 2000) |

#### AiServiceChatRequest

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `message` | text | da |  (lungime min 1; lungime max 1000) Ex.: `"De ce mi-a crescut pulsul de noapte?"` |
| `history` | listă de [AiTurn](#aiturn) | nu |  (max elemente 6) |
| `context` | [AiContext](#aicontext) | da |  |

#### AiCitation

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `title` | text | da |  Ex.: `"Alavi et al. (2022), Nature Medicine"` |
| `url` | text | da |  |
| `snippet` | text | da | Fragmentul din corpus folosit efectiv în răspuns. |

#### AiServiceChatResponse

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `answer` | text | da | În română, 3–5 propoziții. |
| `citations` | listă de [AiCitation](#aicitation) | da | Doar fragmentele folosite. Gol = fără sursă. |
| `recommendation_ids` | listă de text | nu |  Ex.: `["immune-2-1"]` |
| `off_topic` | true/false | nu | True = întrebarea nu ține de sănătatea în misiune; `answer` e mesajul fix. |
| `model` | text | da |  Ex.: `"model-3b-Q4_K_M"` |
| `latency_ms` | număr întreg | da |  |

#### AiServiceStatus

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `ready` | true/false | da | False = modelul nu e încărcat; backend-ul trece direct pe catalog. |
| `model` | text \| null | nu |  |
| `mode` | `"local"` \| `"colab_simulation"` \| `"mock"` | da | Unde rulează modelul. Frontend-ul îl afișează onest. |
| `corpus_documents` | număr întreg | nu | Câte documente sunt în index. |

#### AiServiceError

Corpul răspunsurilor 503 (modelul nu răspunde) și 422 (cerere invalidă).

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `error` | obiect | da |  Ex.: `{"code": "model_unavailable", "message": "llama-server nu răspunde."}` |

