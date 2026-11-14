## T09 — Misiunea și mediile

### Pe scurt, ce am făcut (pe înțeles)

Până acum, ora și ziua misiunii erau scrise de mână în mock (mereu „ziua 96, 07:42”). Acum vin din **ceasul real al misiunii** (cel făcut la T02), care merge de 60 de ori mai repede decât timpul real: o zi de misiune durează 24 de minute reale.

Ce s-a schimbat:
- **`GET /mission`** dă ora și ziua din ceas, mediul curent (de exemplu „tranzit spre Marte”) și starea legăturii cu Pământul: cât durează un mesaj într-un sens (700 de secunde de misiune spre Marte, adică ~11,7 secunde reale) și câte pachete așteaptă la coadă în fiecare direcție (numărate din baza de date).
- **`GET /environments`** dă cele 4 medii (stația spațială, baza de pe Lună, tranzitul spre Marte, baza de pe Marte), citite din `data/environments.json`.
- **`PUT /mission/environment`** este comutatorul de mediu. Mediul ales se salvează în baza de date (tabelul `sim_state`). Dacă treci pe stația spațială (ISS), întârzierea legăturii devine 1 secundă. După salvare, serverul anunță frontend-ul prin evenimentul live `environment.changed`.
- **`PUT /sim/clock`** schimbă viteza ceasului fără ca ora să sară (de exemplu de la ×60 la ×120). Poate sări și înainte la o zi viitoare (la 07:00). **Înapoi nu se poate** (409). Generarea zilelor sărite (date, alerte) vine abia la T33; acum se mută doar ceasul.
- La pornire, serverul pune în bază mediul implicit (`mars_transit`).

### Fișiere modificate
- `backend/app/services/mission.py` — scris: starea misiunii, lista mediilor, schimbarea mediului (salvare + eveniment), schimbarea ceasului; `mission_ticker` rămâne schelet pentru T22
- `backend/app/routers/mission.py` — endpoint-urile apelează serviciul (nu mai e mock); textele din Swagger și erorile traduse în engleză
- `backend/app/main.py` — la pornire se salvează mediul implicit în `sim_state` (ceasul îl pornisem deja la T07)
- `backend/tests/routers/test_mission.py` — nou, 8 teste

### Teste adăugate
- `test_mission_starts_on_day_96_in_default_environment` — ziua 96, 2027-04-15 07:0x, `mars_transit`, întârziere 700 s, coada goală
- `test_environments_come_from_data` — cele 4 medii; câmpurile interne (`sources`, `delay_range_s`) nu ajung la frontend
- `test_switch_to_iss_changes_delay_and_publishes` — după `iss`, întârzierea e 1 s, se trimite `environment.changed`, iar `/mission` arată noul mediu
- `test_environment_change_forbidden_for_earth` — medicul de pe Pământ nu poate schimba mediul (403)
- `test_time_scale_changes_without_jumping` — viteza devine 600, ora nu sare, întârzierea reală se recalculează
- `test_clock_cannot_go_back` — ziua 50 → 409, ziua rămâne 96
- `test_clock_cannot_pass_end_of_mission` — ziua 141 → 422
- `test_clock_jumps_forward` — ziua 100 → 2027-04-19 07:0x

### Rezultate
pytest 65 trecute / 0 picate · ruff ok · smoke OK · serverul pornit: `/mission` → ziua 96, 07:00, `mars_transit`, 700 s (11,67 s reale), ×60; după `iss` → 1 s; după ×120 ora a rămas aceeași · editorul: fără probleme

### Endpointuri devenite reale
- `GET /api/v1/mission`
- `GET /api/v1/environments`
- `PUT /api/v1/mission/environment`
- `PUT /api/v1/sim/clock` (viteza reală; saltul de zi mută doar ceasul, generarea datelor vine la T33)

### Texte rămase în română
- **Numele și descrierile mediilor** (de exemplu „Tranzit spre Marte”) vin din `data/environments.json`; conform regulii, `data/` nu se traduce în cod.
- Restul ca înainte: mock-ul din `app/examples.py`, tag-urile din celelalte routere, „Roluri permise” din `main.py`.

### Decizii luate singur
- **Ferestrele de comunicare** (`window_open`, `window_closes_at`, `next_window_at`) sunt T24; până atunci legătura apare mereu deschisă (`window_open = true`).
- Saltul înainte cu `mission_day` mută ceasul real (cu funcția din T02), deși taskul spunea că rămâne mock; altfel `/mission` nu ar fi arătat ziua nouă. Datele zilelor sărite le generează T33.
- `mission_day` egal cu ziua curentă nu face nimic (nu e „înapoi”, dar nici nu mută ora înapoi la 07:00).
- Dacă baza nu se recreează la pornire, mediul salvat rămâne cel ales anterior.
- Atenție, pentru taskurile următoare: tabloul de bord, check-in-ul etc. sunt încă mock și folosesc ziua fixă 96 din `examples.py`; după un salt de zi, ele nu știu încă de ziua nouă (T21, T33).

### Cum verific eu de mână
1. `cd backend; uv run uvicorn app.main:app --port 8000` → /docs, „Authorize” cu `mock-medic`
2. `GET /api/v1/mission` → ziua 96, ora curentă a misiunii (crește cu ~1 minut la fiecare secundă reală)
3. `PUT /api/v1/mission/environment` cu `{"environment":"iss"}` → `link.one_way_delay_s = 1`; `PUT /api/v1/sim/clock` cu `{"mission_day":50}` → 409

### Mesaj de commit propus
backend: T09 misiunea și mediile

### Următorul task
T10 (dependențele lui sunt gata: da, T05)
