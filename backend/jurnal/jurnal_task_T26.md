## T26 — Furtuna: avertizarea DONKI prin coadă

### Pe scurt, ce am făcut (pe înțeles)

Asta e **cifra din pitch**: cu câte minute a fost SHADOW mai rapid decât Pământul.

În realitate, NASA a trimis prima alertă pentru furtuna din 11 mai 2024 (`20240511-AL-006`) la **20 de minute** după începutul evenimentului. Pe drumul spre Marte, acea alertă mai face și **700 de secunde de misiune** (~11,7 minute) până la navă. SHADOW, în schimb, vede furtuna direct pe dozimetrul de la bord.

Ce face acum backend-ul:
- La `sep/start` se programează avertizarea Pământului la **începutul furtunii + 20 de minute** (decalajul real, citit din fișierul DONKI).
- Când vine momentul, simulatorul pune în coadă un pachet **`donki_alert`**, pe direcția **Pământ → navă**, cu evenimentul DONKI înăuntru. Pachetul merge prin coada de la T23–T24, cu întârzierea legăturii.
- Când pachetul ajunge la bord, se notează ora sosirii (`earth_warning_arrived_at`) și se calculează **`lead_minutes` = sosirea avertizării − alerta de la bord**, în minute de misiune. Avertizarea apare și în mesajele echipajului (`/crew/{id}/messages`), pentru toți astronauții.
- Dacă doza acumulată de la începutul furtunii ar trece de **10% din limita NASA de 250 mGy-Eq** (25 mSv, din `parameters.json`), alerta urcă la **nivelul 3** și pleacă singură spre Pământ ca pachet `alert_l3`. (Cu curba noastră sintetică, doza rămâne mult sub prag.)

**Pe serverul pornit, la ×60:** alerta de la bord la 10 s reale, avertizarea Pământului la 35 s → **`lead_minutes = 25,2`**: SHADOW a fost cu ~25 de minute de misiune mai rapid.

### Fișiere modificate
- `backend/app/services/radiation.py` — programarea avertizării, pachetul `donki_alert`, calculul `lead_minutes` (`donki_arrived`), nivelul 3
- `backend/app/link/scheduler.py` — la livrarea unui `donki_alert` se calculează `lead_minutes`
- `backend/app/simulator/live.py` — avertizarea pleacă din pasul live
- `backend/tests/link/test_donki_uplink.py` — nou, 2 teste

### Teste adăugate
- `test_lead_minutes_is_delay_plus_nasa_lag` — cu ceasul mutat minut cu minut: avertizarea ajunge la 20 min + 700 s după începutul furtunii; `lead_minutes` e pozitiv și egal cu întârzierea + decalajul NASA − momentul alertei de la bord; pachetul e livrat; mesajul apare la astronaut
- `test_warning_leaves_at_the_nasa_alert_time` — la 19 minute nu a plecat nimic; la 20 de minute pachetul e pe drum

### Rezultate
pytest **230 trecute / 0 picate** · ruff ok · smoke OK · demo pe server: `lead_minutes = 25,2`

### Endpointuri devenite reale
- `lead_minutes` și `earth_warning_arrived_at` în `GET /api/v1/radiation/status`
- `donki_alert` în `GET /api/v1/crew/{crew_id}/messages`

### Texte rămase în română
niciunul nou

### Decizii luate singur
- **Expeditorul** avertizării: „Mission Control (NASA DONKI)”; textul mesajului la bord: „Solar particle event warning (2024-05-11T02:10:00-SEP-001).”
- Dacă alerta de la bord nu a venit încă atunci când sosește avertizarea, `lead_minutes` rămâne `null`.
- Doza în „mSv” e tratată ca mGy-Eq pentru pragul de nivel 3 (simplificare de prototip).

### Cum verific eu de mână
1. Pornește serverul; ca `mock-medic`: `POST /api/v1/sim/sep/start`
2. După ~35 s reale, ca `mock-specialist2`: `GET /api/v1/radiation/status` → `lead_minutes` ≈ 25; `GET /api/v1/crew/cm-2/messages` → avertizarea DONKI

### Mesaj de commit propus
(comun cu T25 și T27, vezi `jurnal_task_T27.md`)
