## T34 — Scoaterea mock-ului și verificarea finală

### Pe scurt, ce am făcut (pe înțeles)

Până acum, în backend exista un fișier cu **date de exemplu** (`app/examples.py`), cu care frontend-ul putea lucra încă din prima zi. Toate endpoint-urile au trecut între timp pe date reale, deci fișierul nu mai era folosit. L-am **șters**.
- Mai rămăsese o singură folosire, în `deps.py`: verificarea că un astronaut (`crew_id`) există se făcea pe lista de exemplu. Acum se face **în baza de date**.
- `/health` spune acum `"mode": "real"`.
- **Tokenurile mock** (`mock-medic` etc.) sunt oprite în `.env`-ul de demo (`ALLOW_MOCK_TOKENS=false`). Frontend-ul folosește login-ul real cu parolă, deci nu are nevoie de ele.
- Testele și smoke-ul încă se loghează cu tokenuri mock, așa că le pornesc singure cu `ALLOW_MOCK_TOKENS=true`.
- În `app/` nu mai e niciun `NotImplementedError`: tot drumul demo-ului e implementat.

**Despre mesajul colegului de la AI:** ce cere el (`/ai/chat` și `/ai/status` cheamă serviciul de pe portul 8001, limită de 20 s, apoi textul din catalog) era **deja făcut la T31**. A fost verificat pe server în ambele cazuri:
- cu serviciul AI pornit, răspunsul vine de la model;
- cu serviciul oprit, răspunsul vine din catalog.

Codul e în `app/services/ai.py`. Routerul `app/routers/ai.py` doar îl cheamă, după regula „routere subțiri”.

### Fișiere modificate
- `backend/app/examples.py` — **șters**
- `backend/app/deps.py` — verificarea existenței astronautului, din baza de date
- `backend/app/main.py` — `/health` → `"mode": "real"`
- `backend/pyproject.toml` — scoasă excepția de lint pentru `examples.py`; comentariile traduse în engleză; adăugat `numpy` la dependențele de dezvoltare
- `backend/uv.lock` — `numpy`
- `backend/tests/conftest.py` — testele pornesc cu `ALLOW_MOCK_TOKENS=true`
- `backend/.env` (local, nu intră în git) — `ALLOW_MOCK_TOKENS=false`
- `backend/handoff/04_SCHELET.md` — regenerat cu `scripts/build_handoff.py`
- `scripts/smoke.py` (în afara `backend/`) — conturile și parolele de test se citesc din `backend/seed/users.json`, nu din mock; `ALLOW_MOCK_TOKENS=true` pentru smoke

### De ce `numpy`
Smoke-ul verifică și serviciul AI al colegilor. Acesta importă acum `numpy` (pentru căutarea în baza de cunoștințe). Venv-ul backend-ului nu-l avea în lista lui, așa că smoke-ul pica. L-am adăugat **doar la dependențele de dezvoltare**: aplicația backend nu-l folosește.

### Teste
Niciun test nou: comportamentul nu s-a schimbat, doar s-a scos codul vechi.

### Rezultate
pytest **263 trecute / 0 picate** · ruff ok · `/evidence/tests` → 111 trecute / 0 picate (gata la ~25 s după pornire)

Smoke OK. Pe server, cu tokenurile mock oprite:
- `/health` → `mode: real`;
- un token mock → **401**;
- login-ul real merge pentru medic, astronaut și Pământ;
- AI-ul oprit → răspuns din catalog;
- check-in, pachet falsificat respins, senzor înghețat, salt la ziua 98, reset → ziua 96, iar tokenul rămâne valabil.

Editorul nu arată probleme.

### Ce n-am făcut (în afara `backend/`)
- **`scripts/build_docs.py`** (scrie în `contract/`) și **`scripts/gen_types.sh`** (scrie în `frontend/`) nu i-am rulat: regulile nu-mi dau voie să modific acele foldere. Contractul nu s-a schimbat, deci nu e nimic nou de generat. Dacă vreți totuși să-i rulați, o face cine are grijă de `contract/` și `frontend/`.
- **`scripts/build_handoff.py`** încă scrie „mock → Txx” la routere în `04_SCHELET.md`: are regula „orice router = mock” scrisă în cod. N-am avut voie să modific scriptul. Ca să dispară, trebuie scoase cele două rânduri `elif "routers" in p.parts: state = "mock → …"` din funcția `describe`.
- Tot scriptul ăsta se oprea pe fișierele temporare ale bazei SQLite (`shadow.sqlite-wal` și `shadow.sqlite-shm`), rămase după rularea serverului. Le-am șters, pentru că baza se reface oricum la pornire. Data viitoare scriptul poate da aceeași eroare dacă serverul a rulat înainte: ar trebui să ignore și extensiile `.sqlite-wal` și `.sqlite-shm`.
- **Demo-ul cu frontend-ul pornit** nu l-am putut repeta eu (nu am browser). L-am repetat complet prin API, cu login real. Rămâne de făcut o trecere de mână prin interfață.

### Cum verific eu de mână
1. Pornește backend-ul: `GET /health` → `"mode": "real"`
2. Login cu un cont din `seed/users.json`, apoi folosește tokenul primit; `Bearer mock-medic` → 401
3. Pornește și frontend-ul și fă demo-ul din interfață

### Mesaj de commit propus
backend: T34 scos mock-ul (examples.py), /health în modul real, tokenurile mock oprite în demo, verificarea finală
