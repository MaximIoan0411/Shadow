## T32 — Măsurători de la dispozitive, respingeri, dovezi

### Pe scurt, ce am făcut (pe înțeles)

**Măsurătorile de la dispozitive** (brățara, termometrul…) intră prin `POST /ingest/measurements`. Fiecare e semnată de dispozitiv. Backend-ul o verifică, în ordine:
1. **Semnătura** — dacă nu se potrivește cu cheia dispozitivului (sau dispozitivul e necunoscut), măsurătoarea e **respinsă** („bad_signature”). Așa nu poate băga cineva date false.
2. **Plauzibilitatea** — un puls de noapte de 400 bpm e imposibil → respinsă („implausible”), cu intervalul posibil în mesaj.
3. **Senzorul înghețat** — aceeași valoare exactă de **20 de ori la rând** de la același dispozitiv → respinsă („frozen_sensor”).

O măsurătoare respinsă **nu dă eroare** (răspunsul e tot 200, cu `accepted = false`); se salvează ca **respingere** și pleacă evenimentul live `measurement.rejected`. Una bună se salvează (`source = device`) și trece prin motor, ca orice dată nouă.

**`GET /security/rejections`** arată acum respingerile reale, cele mai noi primele, inclusiv **pachetele respinse de coadă** (de exemplu pachetul falsificat de la T33).

**Ecranul Evidence:**
- `GET /evidence/tests` — la pornirea serverului se rulează o dată testele motorului (`pytest tests/engine`), în fundal, și se păstrează rezultatul: pe server, **111 trecute, 0 picate**.
- `GET /evidence/parameters` — pragurile din `parameters.json`, cu sursa fiecăruia (mutat din mock în serviciu).

`simulator/devices.signed_measurement` produce o măsurătoare semnată exact în forma așteptată.

### Fișiere modificate
- `backend/app/services/security_log.py` — scris tot: primirea măsurătorilor, respingerile, pragurile, testele pentru Evidence
- `backend/app/simulator/devices.py` — `signed_measurement`
- `backend/app/routers/security.py` — `rejections`, `ingest`, `evidence/*` reale
- `backend/app/link/scheduler.py` — un pachet respins la sosire se scrie și în respingeri
- `backend/app/main.py` — testele pentru Evidence rulează o dată la pornire
- `backend/tests/security/test_ingest.py` — nou, 8 teste

### Teste adăugate
- `test_valid_measurement_is_saved` — o măsurătoare bună e acceptată
- `test_tampered_measurement_is_rejected` — semnătura „invalid” și un dispozitiv necunoscut → `bad_signature`
- `test_pulse_400_is_implausible` — puls 400 → `implausible`
- `test_twenty_identical_values_are_a_frozen_sensor` — primele 19 acceptate, a 20-a → `frozen_sensor`
- `test_rejections_list_newest_first` — lista respingerilor, cea mai nouă prima
- `test_parameters_come_from_data` — pragurile cheie din `parameters.json`
- `test_junit_report_parsing` — citirea raportului pytest (trecute / picate / sărite)
- `test_engine_tests_run_for_the_evidence_screen` — rularea reală a testelor motorului: 0 picate, `test_nightsignal_red_after_two_nights` e în listă

### Rezultate
pytest **263 trecute / 0 picate** · ruff ok · smoke OK · pe server: `/evidence/tests` → 111 trecute / 0 picate

### Endpointuri devenite reale
- `POST /api/v1/ingest/measurements`, `GET /api/v1/security/rejections`, `GET /api/v1/evidence/tests`, `GET /api/v1/evidence/parameters`

### Texte rămase în română
- Numele și explicațiile pragurilor vin din `data/parameters.json`.
- Mesajele de respingere sunt în engleză (nu le-am luat pe cele în română din `security/validation.py`, ci doar tipul problemei).

### Decizii luate singur
- **Testele pentru Evidence rulează o singură dată pe proces**, la pornire, într-un thread (nu le oprește `/sim/reset`); fișierul cu rezultatele e creat, citit și șters în același thread. Până se termină (câteva secunde), endpoint-ul întoarce un raport gol.
- **Semnătura** e verificată cu codul provizoriu al securității (acceptă orice semnătură nevidă în afară de „invalid”); când securitatea trece la Ed25519 real, nu trebuie schimbat nimic aici.
- Câmpul `pulse_bpm` din check-in e folosit ca limită pentru `resting_pulse_bpm` de la dispozitive.

### Cum verific eu de mână
1. `POST /api/v1/ingest/measurements` cu `{"device_id":"wearable-cm-3","crew_id":"cm-3","metric_key":"night_pulse_bpm","value":400,"unit":"bpm","measured_at":"2027-04-15T03:00:00Z","signature_b64":"x"}` → `accepted: false`, `implausible`
2. Ca `mock-medic`: `GET /api/v1/security/rejections` → respingerea
3. `GET /api/v1/evidence/tests` (la câteva secunde după pornire) → 111 trecute

### Mesaj de commit propus
(comun cu T31 și T33, vezi `jurnal_task_T33.md`)
