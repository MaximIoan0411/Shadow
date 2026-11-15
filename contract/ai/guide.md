# SHADOW — contractul backend ↔ serviciul AI

**Versiunea {{VERSION}}** · serviciul ascultă pe portul **8001** · singurul lui client: **backend-ul**

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
| `context.open_alerts` | doar fără `alert_id`: alertele nerezolvate ale membrului (cel mult 5, cea mai gravă prima), fiecare cu ce spune catalogul să facă. Ofițerul medical primește alertele unui coleg doar de la nivelul 2 |
| `context.zones` | doar fără `alert_id`: starea celor patru zone de pe corp, din tabloul de bord |

Fără `alert_id`, serviciul răspunde din alertele deschise și din zone (când întrebarea e despre starea
astronautului) sau din surse (când sursele găsite sunt despre alt subiect decât alertele), ori marchează
`off_topic`. Un răspuns care spune că astronautul e bine, cu o alertă deschisă, e înlocuit în cod cu lista
alertelor (`guard.hides_open_alert`), ca un răspuns cu medicament.

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

{{REF_TOC}}

{{REFERENCE}}

## 8. Modelele

{{MODELS}}
