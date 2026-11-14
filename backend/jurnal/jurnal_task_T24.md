## T24 — Coada: planificatorul

### Pe scurt, ce am făcut (pe înțeles)

T23 punea pachetele în coadă; acum ele chiar **pleacă și ajung**. Un task din fundal („planificatorul”) face, în fiecare secundă reală:
1. **Plecarea:** pachetele care așteaptă pleacă (fereastra de comunicare e mereu deschisă în prototip). Fiecare primește ora plecării și ora sosirii = plecarea + **întârzierea mediului curent** (Marte: 700 s de misiune; ISS: 1 s). Frontend-ul primește `packet.sent`.
2. **Sosirea:** pachetele a căror oră de sosire a venit sunt **deschise** cu funcția echipei de securitate:
   - dacă sigiliul e bun → **livrat**: conținutul apare în clar, semnătura e marcată validă → `packet.arrived`;
   - dacă cineva a umblat la pachet (de exemplu i-a schimbat antetul după sigilare) → **respins** (`bad_signature`) → `packet.rejected`.
3. **Răspunsul Pământului** legat de o alertă: când ajunge la bord, alerta primește textul (`earth_reply`), istoricul ei „earth_replied”, iar frontend-ul `alert.updated`. Răspunsul apare și în **`GET /crew/{id}/messages`** (mesajele sosite la bord: răspunsurile pentru acel astronaut și avertizările de furtună pentru toți).

Dacă se schimbă mediul (de exemplu pe ISS), pachetele **deja pe drum** își păstrează ora de sosire; doar cele noi folosesc noua întârziere. Dacă un pas al planificatorului dă eroare, eroarea se scrie în log și bucla merge mai departe.

**Verificat pe serverul pornit, pe Marte, la ×60:** pachetul de nivel 3 a stat pe drum **11,5–11,7 s reale** (700 s de misiune) și a fost livrat la **13,1 s** după escaladare (plus până la 1 s cât așteaptă pasul de plecare și până la 1 s pasul de sosire), cu semnătura validă.

### Fișiere modificate
- `backend/app/link/scheduler.py` — `step` (un pas: plecare, sosire, deschidere, livrare sau respingere, răspunsul Pământului) și bucla `link_scheduler`
- `backend/app/link/windows.py` — fereastra (mereu deschisă) și întârzierea pe mediu, din `data/environments.json`
- `backend/app/services/link.py` — mesajele sosite la bord (`messages`)
- `backend/app/main.py` — planificatorul pornește la start (cu `BACKGROUND_TASKS`, vezi T22)
- `backend/tests/link/test_scheduler.py` — nou, 5 teste

### Teste adăugate
- `test_packet_arrives_after_exactly_the_delay` — cu ceasul înghețat: la 699 s nu a ajuns, la 700 s a ajuns; livrat, semnătura validă, conținutul vizibil pentru Pământ
- `test_tampered_header_is_rejected` — antet modificat după sigilare → respins, `bad_signature`, fără conținut
- `test_earth_reply_reaches_the_astronaut_after_the_second_delay` — răspunsul Pământului apare la astronaut abia după a doua întârziere; alerta primește `earth_reply` și „earth_replied”; alt astronaut nu-l vede
- `test_environment_change_keeps_arrival_of_packets_in_transit` — după trecerea pe ISS, pachetul deja pe drum are tot 700 s, cel nou 1 s
- `test_scheduler_loop_survives_an_error` — o eroare într-un pas nu oprește bucla

### Rezultate
pytest **211 trecute / 0 picate** · ruff ok · **smoke OK** · serverul pornit: pachet spre Marte livrat după ~11,7 s reale pe drum · editorul: fără probleme

### Endpointuri devenite reale
- `GET /api/v1/crew/{crew_id}/messages`
- livrarea pachetelor (stările `in_transit` / `delivered` / `rejected` din `/link/packets`)

### Texte rămase în română
niciunul nou

### Decizii luate singur
- **Ora livrării** e ora pasului care a văzut sosirea (cel mult o secundă reală după ora de sosire).
- **Retrimiterea (replay)**: baza refuză deja două pachete cu același `seq` pe aceeași direcție (`UNIQUE`); un test de atac cu replay vine la T33.
- Mesajele de furtună (`donki_alert`) apar pentru tot echipajul; textul lor se completează la T26.

### Cum verific eu de mână
1. `cd backend; uv run uvicorn app.main:app --port 8000`
2. Ca `mock-medic`: `POST /api/v1/alerts/al-0001/escalate` cu `{"to_level": 3}`; ca `mock-earth`: `GET /api/v1/link/packets/pk-0001` de câteva ori → `in_transit` cu `eta_real_s` care scade, apoi `delivered` după ~12 s, cu `payload`
3. Ca `mock-earth`: `POST /api/v1/earth/replies` cu `{"crew_id":"cm-2","alert_id":"al-0001","body":"Rest."}`; după ~12 s, ca `mock-specialist2`: `GET /api/v1/crew/cm-2/messages` → răspunsul

### Mesaj de commit propus (comun pentru T22, T23 și T24)
backend: T22, T23, T24 evenimentele live (tick real, ping, filtrare pe rol); coada spre Pământ cu pachete sigilate; planificatorul care le trimite, le livrează sau le respinge

### Următoarele taskuri
T25 și T26 (dependențele: T25 — da, T16; T26 — da, T24 și T25 după T25)
