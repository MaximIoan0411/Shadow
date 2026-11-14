## T33 — Demo: reset, salt de zi, atacuri

### Pe scurt, ce am făcut (pe înțeles)

Butoanele de demo merg acum pe date reale:

- **`POST /sim/reset`** — „de la capăt”: oprește taskurile din fundal, golește toate tabelele, reface totul exact ca la pornire (același scenariu → aceleași date, aceleași alerte), pune ceasul în ziua 96 la 07:00, șterge blocările de cont și pornește din nou taskurile. Durează **~1,8 secunde**. Frontend-ul primește `mission.tick` și `dashboard.changed` („reset”). Tokenurile rămân valabile.
- **`PUT /sim/clock` cu `mission_day`** (doar înainte) — **saltul de zi**: generează datele simulate dintre „acum” și ziua aleasă la 07:00 (măsurători, check-in-uri, exerciții, tastare), rulează motorul peste acele zile (exact ca la pornire: reguli → verificarea pe echipaj → reverificări), apoi mută ceasul. De exemplu, saltul la ziua 98 creează zilele 97 și 98, iar alerta imunitară a lui `cm-2` continuă. Pleacă `dashboard.changed` („jump”).
- **`POST /demo/inject-spoof`** — un **pachet falsificat** (semnat cu o cheie greșită) intră în coada spre Pământ; la sosire, coada îl **respinge** (`bad_signature`), iar el apare în `/security/rejections`.
- **`POST /demo/frozen-sensor`** — un dispozitiv trimite **aceeași temperatură de 20 de ori**; validarea o respinge pe a 20-a (`frozen_sensor`).

**Repetiția completă a demo-ului, de două ori la rând, cu reset între ele** (pe serverul real, cu serviciul AI pornit): medic AI → check-in (decalaj 27,3, „alert”) → pachet falsificat → senzor înghețat → salt la ziua 98 → pachetul falsificat respins după 14 s → reset în 1,7–1,8 s → **ziua 96, aceleași alerte, zero respingeri**. Ambele repetiții au ieșit identic.

### Fișiere modificate
- `backend/app/services/demo.py` — scris tot: reset, salt de zi, pachet falsificat, senzor înghețat
- `backend/app/routers/demo.py` — `inject-spoof`, `frozen-sensor`, `reset` reale (nu mai e nimic mock în fișier)
- `backend/app/services/mission.py`, `backend/app/routers/mission.py` — saltul de zi generează zilele; `dashboard.changed` („jump”)
- `backend/app/main.py` — pornirea împărțită în `bootstrap` (baza, datele, istoricul, replay-ul, ceasul) și `start_tasks` / `stop_tasks`, ca resetul să le refolosească
- `backend/app/db/seed.py` — `write_days`: scrie zilele generate dintr-un interval de timp (folosit la pornire și la salt)
- `backend/app/services/pipeline.py` — `replay_days`: replay-ul pe un interval de zile (pornire și salt)
- `backend/app/services/exercise.py` — `score_days`: scorurile exercițiilor pe un interval
- `scripts/smoke.py` (în afara `backend/`) — `BACKGROUND_TASKS=false` (smoke nu are nevoie de taskurile live; durează 19 s în loc de 60 s); un rând, editat de mână
- `backend/tests/routers/test_demo.py` — nou, 4 teste

### Teste adăugate
- `test_reset_brings_back_day_96_and_the_replay_alerts` — după salt, check-in și furtună, resetul (sub 5 s) readuce ziua 96, exact aceleași alerte, fără furtună și fără check-in-ul de azi
- `test_jump_to_day_98_creates_days_97_and_98` — saltul la 98: ora 07:00 din ziua 98, pulsul de noapte pentru 97–98, check-in-ul din ziua 97, istoricul pe 98 de zile, alerta imunitară continuă
- `test_forged_packet_is_rejected_by_the_queue` — pachetul falsificat ajunge `rejected` / `bad_signature` și apare în respingeri
- `test_frozen_sensor_demo` — a 20-a valoare identică → `frozen_sensor`

### Rezultate
pytest **263 trecute / 0 picate** · ruff ok · **smoke OK** (19 s) · repetiția demo-ului de 2 ori la rând cu reset: identică · pornirea `1.83 s` · editorul: fără probleme

### Endpointuri devenite reale
- `POST /api/v1/sim/reset`, `PUT /api/v1/sim/clock` (saltul de zi), `POST /api/v1/demo/inject-spoof`, `POST /api/v1/demo/frozen-sensor`

### Texte rămase în română
niciunul nou

### Decizii luate singur
- **Resetul golește tabelele** (`drop_all` + `create_all`) în loc să șteargă fișierul bazei, care e deschis; sesiunea cererii se închide înainte, ca să nu blocheze baza.
- **Jurnalul de acces și tokenurile revocate** (ținute în memorie de codul provizoriu al securității) **nu** se șterg la reset: sunt dovezi de securitate, iar tokenurile trebuie să rămână valabile.
- **Saltul de zi** nu pornește singur furtuna solară din ziua 97 a scenariului (ea rămâne pe butonul `sep/start`, ca să o controlați în demo).
- Check-in-ul zilei la care sare ceasul nu se generează (îl face astronautul live), la fel ca la pornire.
- **Senzorul înghețat** folosește temperatura lui `cm-4` (36,6 °C, normală), ca demo-ul să nu creeze alerte medicale în plus.
- Am ajustat `smoke.py` să ruleze fără taskurile din fundal: cu ele, resetul din smoke oprea și rularea testelor pentru Evidence la mijloc (eroare `PermissionError` pe fișierul temporar, reparată și în cod).

### Cum verific eu de mână
1. Pornește backend-ul; ca `mock-medic`: `PUT /api/v1/sim/clock` cu `{"mission_day": 98}` → ziua 98; `GET /api/v1/crew/cm-2/timeline` → 98 de zile
2. Ca `mock-earth`: `POST /api/v1/demo/inject-spoof`; după ~14 s, `GET /api/v1/link/packets/<id>` → `rejected`
3. Ca `mock-medic`: `POST /api/v1/sim/reset` → `GET /api/v1/mission` → ziua 96

### Mesaj de commit propus (comun pentru T31, T32 și T33)
backend: T31, T32, T33 puntea către medicul AI cu fallback pe catalog; măsurătorile semnate de la dispozitive, respingerile și dovezile; demo-ul real (reset, salt de zi, pachet falsificat, senzor înghețat)

### Următorul task
T34 — scoaterea mock-ului și verificarea finală (dependențele: toate gata)
