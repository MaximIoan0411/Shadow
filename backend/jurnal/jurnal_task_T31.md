## T31 — Puntea către medicul AI

### Pe scurt, ce am făcut (pe înțeles)

„Medicul AI” e un model de limbaj care rulează separat (serviciul din `ai/`, portul 8001) și care **reformulează** recomandarea din catalog, cu surse NASA. **Nu decide nimic**: nivelul alertei îl dă motorul. Backend-ul e singurul care vorbește cu el.

Ce face acum `POST /ai/chat`:
- **Construiește contextul** pentru AI: subiectul și nivelul alertei, titlul, dovezile, recomandarea din catalog (cu sursa ei), ziua misiunii și mediul. **Fără nume și fără `crew_id`**: AI-ul nu știe cine întreabă.
- **Întreabă serviciul AI**, cu o limită de **20 de secunde**. Conexiunea la baza de date se închide înainte de așteptare, ca să nu blocheze baza cât timp „gândește” modelul.
- **Dacă AI-ul nu răspunde** (oprit, prea lent, eroare), endpoint-ul **nu dă eroare**: întoarce textul recomandării din catalog, cu sursa, și `fallback = true`. Aplicația merge și fără AI.
- Astronautul poate întreba doar despre propriile date (altfel 403).
- `GET /ai/status` spune dacă modelul e pornit; dacă serviciul nu răspunde → `ready = false`, `mode = "fallback"`.

**Verificat pe server**, cu serviciul AI mock din `ai/` pornit: răspunsul a venit de la AI (`fallback = false`, cu o citare). Cu serviciul oprit (de exemplu în smoke) → răspunsul din catalog.

### Fișiere modificate
- `backend/app/services/ai.py` — scris tot: contextul, apelul cu limită de timp, fallback-ul, starea
- `backend/app/routers/ai.py` — endpoint-urile reale; textele în engleză
- `backend/tests/routers/test_ai_bridge.py` — nou, 4 teste (cu `httpx.MockTransport`, fără să pornească serviciul AI)

### Teste adăugate
- `test_ai_down_falls_back_to_the_catalog` — AI oprit → 200, `fallback = true`, textul și sursa din catalog; `/ai/status` → `fallback`
- `test_ai_down_without_alert_still_answers` — fără alertă și fără AI → tot un răspuns
- `test_ai_up_answer_comes_from_the_service` — AI pornit → răspunsul și citarea vin din serviciu; contextul are alerta și recomandarea, dar **nu** conține `cm-2` sau numele astronautului
- `test_astronaut_asks_only_about_themselves` — despre alt astronaut → 403

### Rezultate
pytest **263 trecute / 0 picate** (împreună cu T32–T33) · ruff ok · smoke OK · pe server, cu `ai/` pornit: `fallback=False`, `model=mock`, 1 citare

### Endpointuri devenite reale
- `POST /api/v1/ai/chat`, `GET /api/v1/ai/status`

### Texte rămase în română
- Textele recomandărilor (folosite la fallback) vin din `data/catalog/recommendations.json`.

### Decizii luate singur
- **Disclaimer-ul** e trimis explicit în engleză („Decision-support prototype, not a medical device.”); valoarea implicită din `schemas.py` (contract) e în română, n-am atins-o.
- Fără alertă și fără AI, răspunsul e un text general scurt, fără citare.
- Istoricul conversației trimis la AI e tăiat la ultimele 6 mesaje (cât acceptă contractul serviciului).
- O alertă a altui astronaut în `alert_id` → 422.

### Cum verific eu de mână
1. `cd ai; uv run uvicorn service.main:app --port 8001` și, separat, backend-ul
2. Ca `mock-specialist2`: `POST /api/v1/ai/chat` cu `{"crew_id":"cm-2","message":"Why is my night pulse up?","alert_id":"<id-ul alertei imunitare>"}` → `fallback: false`
3. Oprește serviciul AI și repetă → `fallback: true`, textul din catalog

### Mesaj de commit propus
(comun cu T32 și T33, vezi `jurnal_task_T33.md`)
