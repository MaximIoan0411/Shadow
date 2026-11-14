## T07 — Autentificarea reală

### Pe scurt, ce am făcut (pe înțeles)

Până acum login-ul era „de jucărie”: verifica parola, dar dădea un bilet fix, `mock-specialist2`, pe care oricine îl putea scrie de mână. Acum login-ul e real:

- **Login:** serverul caută contul în baza de date (cea creată la T06) și verifică parola cu hash-ul salvat. Dacă e corectă, emite un **token JWT**: un „bilet” semnat cu o cheie secretă (`JWT_SECRET`), în care scrie cine ești (`u-cm-2`), ce rol ai (`astronaut`) și ce membru al echipajului ești (`cm-2`). Biletul expiră după 12 ore. Nimeni nu-l poate falsifica fără cheia secretă; dacă cineva schimbă o literă din el, serverul îl respinge.
- **La fiecare cerere** cu un bilet, serverul îi verifică semnătura și expirarea, verifică dacă nu a fost anulat (logout), apoi încarcă contul. **Rolul și membrul echipajului se iau doar din bilet**, niciodată din ce trimite cererea, deci un astronaut nu se poate da drept altul.
- **Logout:** biletul se trece pe o listă de bilete anulate; după logout, același bilet nu mai merge (401).
- **Protecția la ghicit parole:** după 5 parole greșite pe un cont, contul se blochează 60 de secunde (429). Blocarea e doar pe acel cont; ceilalți astronauți se pot autentifica normal.
- **Cont inexistent:** serverul verifică totuși o parolă „de umplutură”, ca răspunsul să dureze la fel și să nu se poată afla ce conturi există. Mesajul de eroare e același: „Wrong username or password.”
- **Jurnalul de acces:** fiecare login reușit, fiecare login eșuat și fiecare logout se scrie în jurnal.
- **Lista de conturi** de pe ecranul „Who are you?” vine acum din baza de date.
- Biletele vechi `mock-<utilizator>` merg în continuare cât timp `ALLOW_MOCK_TOKENS=true` (testele, smoke și frontend-ul pe mock le folosesc). Cu `false` sunt respinse.

Toată criptografia (semnarea biletului, hash-ul parolelor, blocarea) e codul echipei de securitate; eu doar l-am apelat în ordinea cerută de contract.

### Fișiere modificate
- `backend/app/services/auth.py` — scris tot: lista conturilor, login, logout, citirea contului din token
- `backend/app/routers/auth.py` — endpoint-urile apelează serviciul; scos mock-ul (`_HASHES`, `examples.USERS`); textele din Swagger traduse în engleză (tag „1. Authentication”)
- `backend/app/deps.py` — `current_user` e acum `async`, primește sesiunea bazei și verifică tokenul real; `get_app_settings` nou; scos `decode_token` (mock)
- `backend/app/main.py` — la pornire **pornește ceasul misiunii** (ziua 96, 07:00), necesar pentru ora din jurnalul de acces
- `backend/seed/users.json` — numele afișate traduse în engleză (Commander, Mission Specialist 2, Crew Medical Officer, Flight Engineer, Flight Surgeon); utilizatorii și parolele neschimbate
- `backend/tests/security/test_auth_flow.py` — nou, 11 teste

### Teste adăugate
- `test_login_returns_real_token_that_works_on_me` — login-ul dă un JWT real care merge la `/auth/me`
- `test_logout_revokes_the_token` — după logout, același token dă 401
- `test_other_accounts_password_is_rejected` — parola altui cont dă 401 `invalid_credentials`
- `test_unknown_user_gets_same_error` — cont inexistent: aceeași eroare
- `test_five_wrong_passwords_lock_only_that_account` — 5 greșeli → 429 pe acel cont; alt cont merge
- `test_role_and_crew_come_only_from_token` — tokenul lui `cm-2` vede doar datele lui `cm-2`
- `test_tampered_token_is_rejected` — un token modificat dă 401
- `test_login_and_failures_are_written_to_access_log` — în jurnal apar `login_failed` și `login`
- `test_accounts_come_from_database` — cele 5 conturi, 4 la bord și 1 pe Pământ
- `test_mock_token_accepted_when_allowed` — `mock-specialist2` merge cu `ALLOW_MOCK_TOKENS=true`
- `test_mock_token_rejected_when_not_allowed` — cu `false` dă 401, dar tokenul real merge

### Rezultate
pytest 49 trecute / 0 picate · ruff ok · **smoke: PICĂ** (vezi mai jos) · serverul pornește; login real → `/me` → logout → 401 verificate de mână · editorul: fără probleme

**De ce pică smoke:** `scripts/smoke.py` creează aplicația cu `TestClient(app)` fără `with`, deci **nu rulează pornirea** (`lifespan`): nu există baza de date, nici conturile. Până acum nu conta, pentru că totul era mock. De la T07, login-ul și orice cerere autentificată au nevoie de bază. Eroarea: `TypeError: 'NoneType' object is not callable` în `get_session`.
**Reparația** e un singur rând în `scripts/smoke.py` (în afara `backend/`, deci nu l-am atins): `c = TestClient(app)` → `c = TestClient(app).__enter__()`. Am încercat-o pe o copie în folderul temporar: **smoke trece complet** (`OK: API 56 endpoint-uri + permisiuni + conturi separate + reguli 1.2 …`). Aștept decizia ta.

### Endpointuri devenite reale
- `GET /api/v1/auth/accounts`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- plus verificarea tokenului la toate endpoint-urile protejate (`deps.current_user`)

### Texte rămase în română
- Mock-ul din `app/examples.py` (de exemplu „Specialist de misiune 2” în tabloul de bord mock), tag-urile din celelalte routere, „Roluri permise” din `main.py`, textele din `data/`.
- Exemplele din `app/schemas.py` (contract, neatinse).

### Decizii luate singur
- **Am pornit ceasul misiunii la pornire** (pasul 1 din T09, aceeași comandă), pentru că jurnalul de acces cere ora misiunii (`clock.now()`). T09 mai are de adăugat doar mediul curent.
- **Am tradus numele afișate în `seed/users.json`** (propunerea de la T06), ca login-ul să întoarcă nume în engleză. Inițialele (CD, S2, OM, IZ, MZ) le-am lăsat neschimbate.
- Tokenul `mock-<u>` se caută acum în baza de date (aceleași conturi), nu în `examples.py`.
- La login eșuat sau blocat, serviciul face `commit` înainte să întoarcă eroarea, ca intrarea din jurnal să nu se piardă când jurnalul va scrie în bază.
- Logout cu un token mock: se scrie în jurnal, dar tokenul rămâne valid (e text fix).
- Contul necunoscut apare în jurnal ca `unknown`.

### Cum verific eu de mână
1. `cd backend; uv run uvicorn app.main:app --port 8000` → http://localhost:8000/docs → `POST /api/v1/auth/login` cu `{"username":"specialist2","password":"cm2-shadow"}` → primești un token lung `eyJ...`
2. „Authorize” cu tokenul → `GET /api/v1/auth/me` → contul tău; `POST /api/v1/auth/logout` → apoi `/auth/me` dă 401
3. Login de 5 ori cu parolă greșită pe `inginer` → a 6-a oară 429

### Mesaj de commit propus
backend: T07 autentificarea reală

### Următorul task
T08 (dependențele lui sunt gata: da, T07), după ce hotărăști cu smoke
