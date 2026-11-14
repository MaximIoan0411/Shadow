## T22 — Evenimentele live

### Pe scurt, ce am făcut (pe înțeles)

Frontend-ul nu întreabă serverul la fiecare secundă „s-a schimbat ceva?”; ține deschisă o singură conexiune, `/events`, pe care serverul îi „împinge” noutățile (Server-Sent Events). Acum:
- **Ceasul misiunii bate live:** un task din fundal trimite `mission.tick` **în fiecare secundă reală**, cu ora și ziua misiunii (la ×60, fiecare tick e cu un minut de misiune mai târziu). Înainte, tick-ul era fals, cu ora fixă din mock.
- **`: ping` la 15 secunde fără evenimente**, ca proxy-urile să nu închidă conexiunea.
- **Fiecare vede doar ce are voie:** astronautul doar evenimentele lui și pe cele generale; medicul de pe Pământ doar `mission.*`, `environment.*` și `packet.*`; ofițerul medical tot. Regula e acum o funcție separată (`deps.visible_to`), testată direct.
- **Ora fiecărui eveniment** (`at`) e ora misiunii, din ceas (înainte venea din mock).
- La schimbarea vitezei sau a zilei (`PUT /sim/clock`) pleacă imediat un `mission.tick`.
- Am verificat că toate serviciile scrise până acum publică evenimentele **după** salvarea în bază.

### Fișiere modificate
- `backend/app/services/mission.py` — `mission_ticker` (bucla de 1 s) și `tick_data`
- `backend/app/routers/events.py` — fluxul SSE fără tick fals, cu `: ping`; generatorul e o funcție testabilă (`stream`); textele în engleză
- `backend/app/deps.py` — `publish` folosește ora misiunii; `visible_to` (cine ce vede)
- `backend/app/routers/mission.py` — `PUT /sim/clock` trimite un `mission.tick`
- `backend/app/main.py` — la pornire se pornesc taskurile din fundal (tick-ul și planificatorul cozii, T24), la oprire se opresc
- `backend/app/config.py` — setarea nouă `BACKGROUND_TASKS` (implicit `true`)
- `backend/tests/conftest.py` — în teste, `BACKGROUND_TASKS=false` (altfel tick-urile ar intra în cozile testelor); comentariile în română scoase
- `backend/tests/routers/test_events.py` — nou, 8 teste

### Teste adăugate
- `test_astronaut_does_not_get_other_members_events` — un eveniment al lui `cm-1` nu ajunge la `specialist2`
- `test_cmo_gets_everything` — ofițerul medical le primește pe toate
- `test_earth_gets_only_mission_and_packets` — Pământul primește doar tick-ul și pachetele
- `test_event_time_is_mission_time` — `at` = ora misiunii (2027-04-15 07:0x), formatul SSE corect
- `test_ping_when_nothing_happens` — fără evenimente vine `: ping`
- `test_ticker_publishes_every_second` — bucla publică tick-uri la rând
- `test_clock_change_sends_a_tick` — schimbarea vitezei trimite un tick
- `test_events_endpoint_requires_auth` — fără token → 401

### Rezultate
pytest **211 trecute / 0 picate** (împreună cu T23–T24) · ruff ok · smoke OK · pe serverul pornit, `curl -N` pe `/events` a arătat un `mission.tick` pe secundă (07:02, 07:03, 07:04, 07:05 ora misiunii)

### Endpointuri devenite reale
- `GET /api/v1/events` (tick-ul real, ping-ul, filtrarea pe rol)

### Texte rămase în română
niciunul nou

### Decizii luate singur
- **`BACKGROUND_TASKS`**: setare nouă, ca testele să ruleze fără taskuri din fundal; în teste planificatorul se apelează pas cu pas.
- Evenimentele publicate direct de routerele încă mock (`security`, `demo`, `radiation`) rămân cum sunt până la taskurile lor (T25, T32, T33).

### Cum verific eu de mână
1. `cd backend; uv run uvicorn app.main:app --port 8000`
2. `curl.exe -N -H "Authorization: Bearer mock-specialist2" http://localhost:8000/api/v1/events` → un `mission.tick` pe secundă

### Mesaj de commit propus
(comun cu T23 și T24, vezi `jurnal_task_T24.md`)
