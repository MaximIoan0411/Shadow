## T21 — Tablou de bord, panouri, derulator

### Pe scurt, ce am făcut (pe înțeles)

Acestea sunt răspunsurile „mari” pentru ecranul astronautului. Până acum veneau toate din mock (date scrise de mână); acum se construiesc din baza de date și din motor:

- **Tabloul de bord** (`GET /crew/{id}/dashboard`) — ecranul principal, într-un singur apel:
  - **cele 4 zone ale corpului**, cu culoarea și scorul fiecăruia: Tastatura (scorul tastării și al PVT-ului), Santinela (pulsul de noapte), iar Inima și Încărcarea pe valori fixe provizorii (regulile lor vin la T27/T28; sunt marcate „date simulate”). Dacă pilonul are o alertă deschisă, zona arată titlul alertei;
  - **decalajul de percepție** din check-in-ul zilei (fără check-in → „unknown”);
  - **alerta principală** (cea mai gravă deschisă) și câte alerte sunt deschise;
  - **seriile de zile** (check-in, antrenament în două sesiuni, test de reacție) și **reamintirile zilei** (check-in 07:00, test de reacție 09:00, a doua sesiune de exerciții 16:00), cu „făcut / întârziat”.
- **Derulatorul** (`?as_of_day=`): același tablou, așa cum arăta la sfârșitul unei zile trecute. Exemplu: în ziua 93, Santinela lui `cm-2` e „ok”; în ziua 95 e deja „alert”. O zi din viitor → 422.
- **Panoul unei zone** (la click pe corp): textele din `data/texts/body_functions.json` (funcția părții corpului, pericolul spațial, limitele oneste, sursele), valorile față de normalul personal, **graficul pe ultimele 10 zile** cu banda normală și pragul (la Santinela: normal + 4 bpm, NightSignal), plus planul alertei deschise.
- **Seria unei metrici** (pentru un al doilea grafic sau un interval mai lung).
- **Istoricul pe zile** (`timeline`): culoarea fiecărui pilon în fiecare zi, din alertele existente (ieftin, fără să ruleze motorul pe 96 de zile), cu etichete ca „Sentinel alert” (ziua 94), „Sentinel alert escalated” (ziua 95), „Solar storm”.
- **Lista echipajului** (doar pentru ofițerul medical): pentru fiecare membru doar starea generală, câte alerte are și nivelul maxim, fără nicio valoare medicală.

**O schimbare importantă pentru demo:** istoricul simulat nu mai scrie check-in-ul zilei de start (96). Astronautul îl face live, iar ecranul arată corect „check-in de făcut” până atunci. Seria de check-in-uri nu se „rupe” dimineața: dacă azi nu e încă făcut, se numără până ieri (95 de zile), iar după check-in devine 96.

**Viteza:** tabloul de bord răspunde în **45–86 ms** local (ținta: sub ~200 ms).

### Fișiere modificate
- `backend/app/services/crew.py` — scris tot: tabloul de bord, panoul, seriile, istoricul pe zile, lista echipajului, verificarea zilei din viitor
- `backend/app/routers/crew.py` — endpoint-urile apelează serviciul (nu mai e mock); textele în engleză
- `backend/app/db/seed.py` — istoricul nu mai scrie check-in-ul zilei de start
- `backend/app/services/checkins.py` — seria de check-in-uri se numără de ieri dacă azi nu e încă făcut
- `backend/tests/routers/test_crew_api.py` — nou, 11 teste
- `backend/tests/routers/test_seed_history.py`, `test_repos.py`, `test_checkin_api.py` — actualizate: 95 de check-in-uri în istoric, nu 96

### Teste adăugate
- `test_cm2_dashboard_now` — `cm-2`: imunitar „alert”, tastare „watch”, 2 alerte, cea principală e imunitară; check-in neefectuat, seria 95, reamintirile
- `test_checkin_updates_dashboard` — după check-in (dispoziția 4): făcut, iar decalajul de percepție devine „alert” (≥ 25)
- `test_cm1_all_ok` — `cm-1`: toate zonele „ok”, nicio alertă
- `test_as_of_day_93_sentinel_ok` — ziua 93: Santinela „ok”; ziua 95: „alert”
- `test_future_day_is_422` — ziua 97 → 422
- `test_dashboard_is_fast` — sub 0,4 s în teste (pe server: 45–86 ms)
- `test_immune_panel` — metricile, graficul pe zilele 87–96, normalul ~54 bpm, pragul = normal + 4, banda, planul, sursele
- `test_behavioral_and_placeholder_panels` — panoul Tastatura și panoul Inima (provizoriu, marcat simulat)
- `test_series` — seria pulsului de noapte, ultimele 3 zile peste prag; o metrică din alt pilon → 404
- `test_timeline` — 96 de zile; ziua 93 ok, 94 „watch”, 95 „alert”; etichetele alertei
- `test_crew_list_for_cmo` — `cm-2` „alert”, 2 alerte, nivel maxim 2; astronautul → 403

### Rezultate
pytest **191 trecute / 0 picate** · ruff ok · **smoke OK** · serverul pornit de 2 ori la rând (`SHADOW startup finished in 1.19 s` / `1.24 s`) · tabloul lui `cm-2` pe server: Tastatura watch 27,6 „Typing 18% slower than usual”, Inima ok 88, Santinela alert 58 „Night pulse +7 bpm, 3 nights in a row”, Încărcarea ok 82; prima cerere 86 ms, a doua 45 ms

### Endpointuri devenite reale
- `GET /api/v1/crew` (ofițerul medical)
- `GET /api/v1/crew/{crew_id}/dashboard` (inclusiv `?as_of_day=`)
- `GET /api/v1/crew/{crew_id}/pillars/{pillar}`
- `GET /api/v1/crew/{crew_id}/pillars/{pillar}/series`
- `GET /api/v1/crew/{crew_id}/timeline`

### Texte rămase în română
niciunul nou (textele din `data/texts/body_functions.json` sunt deja în engleză)

### Decizii luate singur
- **Inima și Încărcarea** au deocamdată valori fixe în tablou (88 „Within your in-flight range”, 82 „Exercise plan on track”), cum cerea taskul, dar cu texte în engleză; panourile lor arată totuși valorile reale din bază față de normalul personal și sunt marcate „date simulate”.
- **Încărcarea** are în panou metrica „Exercise sessions” (sesiuni pe zi), pentru că scorul de încărcare (`loading_score`) e încă 0 până la T28.
- **Semnalele încrucișate** sunt o listă goală (T29), iar **banner-ul de radiații** e `false` (T25).
- **Check-in-ul zilei 96 nu mai e în istoricul simulat** (vezi mai sus); am actualizat trei teste vechi la 95 de check-in-uri.
- O alertă contează la o zi trecută dacă fusese creată până atunci și nu era încă închisă.
- În istoricul pe zile, culoarea unei alerte se ia din istoricul ei: galben din ziua creării, roșu din ziua escaladării.
- Panoul Santinelei are și „Stress index” (T14), cu zilele de izolare = ziua misiunii și fără doză de radiații (T25).

### Cum verific eu de mână
1. `cd backend; uv run uvicorn app.main:app --port 8000` → /docs, „Authorize” cu `mock-specialist2`
2. `GET /api/v1/crew/cm-2/dashboard` → Santinela „alert”, Tastatura „watch”; cu `?as_of_day=93` → Santinela „ok”
3. `GET /api/v1/crew/cm-2/pillars/immune` → graficul pe 10 zile, cu pragul; `GET /api/v1/crew/cm-2/timeline` → 96 de zile

### Mesaj de commit propus (comun pentru T20 și T21)
backend: T20, T21 testul de reacție (pvt-b) real; tabloul de bord, panourile, seriile și derulatorul din bază

### Următoarele taskuri
T22 și T23 (dependențele lor sunt gata: da — T16 pentru T22, T17 pentru T23)
