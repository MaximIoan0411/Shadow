## T25 — Radiații: generator, detector, adăpost

### Pe scurt, ce am făcut (pe înțeles)

Pe drumul spre Marte nava e lovită din când în când de furtuni solare: particule foarte energetice care cresc brusc doza de radiații. Aplicația redă o furtună **reală** din NASA DONKI (11 mai 2024, „Gannon”), dar **forma curbei e inventată** (doza măsurată pentru acel eveniment nu e publicată), iar ecranul o arată ca „sintetică” (`profile_is_synthetic = true`).

Ce face acum backend-ul:
- **Dozimetrul simulat:** în liniște, rata dozei = fondul mediului curent (pe drumul spre Marte 65,8 µSv/h) ± 5% zgomot. La pornire se scriu în bază ultimele **48 de ore de liniște** (o citire la 10 minute), ca să existe media pe 24 h.
- **Furtuna** (`POST /sim/sep/start`): după momentul de început, rata urcă în ~20 de minute până la **de 6 ori fondul** și apoi scade încet, în câteva ore. Cât ține furtuna, simulatorul din fundal face **o citire la fiecare 2 secunde reale**.
- **Detectorul:** când **3 citiri la rând** sunt **cel puțin de 2 ori media pe 24 h** (pragul din `parameters.json`), SHADOW dă **alerta de nivel 1** („Solar particle event: dose rate ×3.7 — go to the shelter”, recomandarea `radiation-1-1`), **câte una pentru fiecare astronaut**, plus evenimentul live `radiation.alert`. Tabloul de bord arată banner-ul „Mergi în adăpost” (`radiation_alert_active`).
- **„Sunt în adăpost”** (`POST /radiation/shelter-ack`): din acel moment rata se înmulțește cu **68/214 ≈ 0,32** (exemplul de ecranare cu saci de apă și bagaje din `parameters.json`). Ieșirea din adăpost o readuce.
- **`GET /radiation/status`**: rata acum, media, raportul, alerta, adăpostul, doza acumulată de la începutul furtunii (mSv); **`GET /radiation/series`**: curba pentru grafic.
- **`POST /sim/sep/stop`**: oprește furtuna (`radiation.cleared`). Alertele rămân deschise; le închide un om.

**Pe serverul pornit, la ×60:** alerta de la bord a venit după **10 secunde reale** (~8–10 minute de misiune), la un raport de ×3,7.

### Fișiere modificate
- `backend/app/simulator/radiation.py` — `dose_rate` (fond, zgomot, forma furtunii, adăpostul)
- `backend/app/engine/radiation.py` — `mean_24h`, `is_alert`, `event_dose_msv`
- `backend/app/services/radiation.py` — scris tot: starea furtunii și a adăpostului, citirile din istoric, starea, seria, pornirea și oprirea furtunii, pasul live (citire, alertă, nivel 3), avertizarea DONKI (T26)
- `backend/app/simulator/live.py` — bucla din fundal (2 s)
- `backend/app/routers/radiation.py`, `backend/app/routers/demo.py` — `status`, `series`, `events`, `shelter-ack`, `sep/start`, `sep/stop` reale; textele fișierelor în engleză (în `demo.py`, atacurile și resetul rămân mock până la T33)
- `backend/app/services/crew.py` — banner-ul de radiații din tabloul de bord
- `backend/app/main.py` — citirile din istoric la pornire; simulatorul live pornește cu celelalte taskuri din fundal
- `backend/tests/engine/test_radiation.py` — nou, 8 teste

### Teste adăugate
- **`test_sep_alert_at_2x_mean`** — 2 citiri peste prag nu dau alertă; 3 la rând da
- `test_mean_and_event_dose` — media și doza acumulată
- `test_dose_rate_shape` — liniștea, vârful de ×6 la 20 de minute, scăderea, adăpostul, același zgomot în același minut
- `test_quiet_background_is_seeded` — media pe 24 h există de la pornire; seria are puncte
- `test_two_readings_above_threshold_no_alert_third_alerts` — cu ceasul mutat de mână: fără alertă la primele 2 citiri peste prag, alertă la a 3-a; 4 alerte (câte una pe astronaut), banner-ul pe tabloul de bord
- `test_shelter_lowers_the_rate` — în adăpost rata scade la 68/214, la ieșire revine
- `test_stop_clears_the_storm` — oprirea șterge furtuna
- `test_unknown_event_and_earth_access` — eveniment necunoscut → 404; Pământul nu vede dozimetrul (403), dar vede lista evenimentelor DONKI

### Rezultate
pytest **230 trecute / 0 picate** (împreună cu T26–T27) · ruff ok · smoke OK · demo pe server: alertă după 10 s reale · editorul: fără probleme

### Endpointuri devenite reale
- `GET /api/v1/radiation/status`, `GET /api/v1/radiation/series`, `GET /api/v1/radiation/events`, `POST /api/v1/radiation/shelter-ack`
- `POST /api/v1/sim/sep/start`, `POST /api/v1/sim/sep/stop`

### Texte rămase în română
niciunul nou

### Decizii luate singur
- **Alerta de radiații e câte una pe astronaut** (alertele sunt legate de un membru al echipajului); `/radiation/status` întoarce în `alert_id` alerta celui care întreabă.
- **Media pe 24 h** e media citirilor de **dinainte** de începutul furtunii (altfel furtuna și-ar ridica singură pragul).
- **Factorul de adăpost 68/214** e calculat din `reducere_doza_adapost_capsula` (taskul spunea „0,3”; valoarea din date e 0,32).
- **Forma curbei** (urcare 20 de minute, scădere în ~3 ore) e aleasă de noi și marcată „sintetică” în cod și în răspuns.
- Doza „mSv” e simplificată (contractul spune „prototipul afișează totul în Sv”).

### Cum verific eu de mână
1. `cd backend; uv run uvicorn app.main:app --port 8000`
2. Ca `mock-medic`: `POST /api/v1/sim/sep/start` cu `{"starts_in_min": 0}`; ca `mock-specialist2`: `GET /api/v1/radiation/status` la câteva secunde → după ~10 s `alert_active = true`
3. `POST /api/v1/radiation/shelter-ack` cu `{"sheltered": true}` → rata scade la ~un sfert

### Mesaj de commit propus
(comun cu T26 și T27, vezi `jurnal_task_T27.md`)
