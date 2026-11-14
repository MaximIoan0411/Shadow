## T08 — Jurnalul de acces

### Pe scurt, ce am făcut (pe înțeles)

Jurnalul de acces e „registrul de la poartă” al aplicației: cine s-a uitat la datele cui, când și dacă a avut voie. E important pentru încredere: un astronaut trebuie să poată vedea cine i-a citit datele medicale.

Ce se scrie acum în jurnal:
- **Ofițerul medical** (`medic`, `cm-3`) are voie să vadă datele oricărui astronaut, dar fiecare citire a datelor altcuiva lasă o urmă: de exemplu „Crew Medical Officer · read_dashboard · crew/cm-2/dashboard · allowed”. Când deschide o alertă, apare `read_alert`.
- **Orice refuz (403)** se scrie ca `access_denied` / `denied`: de exemplu Comandantul care încearcă să vadă tabloul lui `cm-2`, sau medicul de pe Pământ care încearcă să intre la datele echipajului. Am pus asta într-un singur loc, în funcția care transformă erorile în răspunsuri, ca să prindă **toate** refuzurile, oricare ar fi endpoint-ul.
- Un astronaut care își citește propriile date **nu** se scrie (ar umple jurnalul fără folos).
- Login-urile și logout-urile se scriau deja de la T07.
- **În jurnal nu ajung niciodată parole sau tokenuri** (am un test pentru asta).

Citirea jurnalului, `GET /access-log`:
- Astronautul vede doar intrările despre datele lui (chiar dacă cere altceva în `crew_id`, se ignoră).
- Ofițerul medical vede tot jurnalul, sau doar un membru dacă dă `crew_id`.
- Cele mai noi intrări sunt primele; `limit` spune câte.
- Medicul de pe Pământ nu are acces (403).

Notă: jurnalul propriu-zis (`access_log.write`) îl scrie codul echipei de securitate, care deocamdată îl ține **în memorie** (se pierde la repornire). Am făcut citirea astfel încât, când securitatea trece la varianta care scrie în baza de date, endpoint-ul începe singur să citească din bază, fără altă modificare.

### Fișiere modificate
- `backend/app/services/access.py` — scris de la zero: `record` (scrie o intrare), `record_denied` (pentru refuzuri), `entries` (citirea filtrată, cele mai noi primele), plus numele acțiunii după cale (`read_dashboard`, `read_pillar`, `read_alert`)
- `backend/app/deps.py` — `crew_access` scrie în jurnal când ofițerul medical citește datele altui membru; `current_user` ține minte utilizatorul pentru jurnalul refuzurilor
- `backend/app/main.py` — orice eroare 403 se scrie în jurnal ca `access_denied`
- `backend/app/routers/security.py` — `GET /access-log` citește jurnalul real (nu mai e mock); textele fișierului traduse în engleză
- `backend/app/routers/alerts.py` — `GET /alerts/{id}` citit de ofițerul medical → `read_alert`; textele fișierului traduse în engleză (mesaje de eroare, Swagger)
- `backend/tests/security/test_access_log_wiring.py` — nou, 8 teste
- `scripts/smoke.py` (în afara `backend/`, cu acordul tău) — `TestClient(app).__enter__()`, ca smoke să pornească aplicația cu tot cu baza de date (problema de la T07)
- `.gitignore` (rădăcină, cu acordul tău) — adăugat `*.sqlite-wal` și `*.sqlite-shm`

### Teste adăugate
- `test_denied_read_is_logged` — Comandantul la datele lui `cm-2` → 403 și intrare `access_denied` / `denied`
- `test_cmo_reading_another_member_is_logged` — medicul citește `cm-2` → intrare `read_dashboard` / `allowed`
- `test_astronaut_reading_own_data_is_not_logged` — propriile date nu se scriu
- `test_earth_role_denied_is_logged` — refuzul medicului de pe Pământ se scrie
- `test_cmo_reading_alert_is_logged` — medicul deschide `al-1042` → `read_alert`
- `test_no_secrets_in_log` — nicio parolă, niciun token în jurnal
- `test_access_log_endpoint_newest_first_and_filtered` — astronautul vede doar intrările lui, cele mai noi primele; `crew_id` ignorat pentru el; `limit` funcționează
- `test_access_log_endpoint_forbidden_for_earth` — rolul `earth` primește 403

### Rezultate
pytest 57 trecute / 0 picate · ruff ok · **smoke OK** (cu reparația din `scripts/smoke.py`) · serverul pornește; verificat de mână: `GET /access-log` ca `specialist2` arată „Commander · access_denied” și „Crew Medical Officer · read_dashboard” · editorul: fără probleme

### Endpointuri devenite reale
- `GET /api/v1/access-log`
- jurnalizarea la toate endpoint-urile cu `crew_access` (citirile ofițerului medical) și la orice 403

### Texte rămase în română
- În `routers/security.py`, valorile filtrului `topic` („comportamental / cardiovascular / …”) sunt **identificatori** din `data/parameters.json`, nu texte; le-am lăsat.
- Restul ca înainte: mock-ul din `app/examples.py`, tag-urile din celelalte routere, „Roluri permise” din `main.py`, textele din `data/`.

### Decizii luate singur
- Refuzurile (403) le scriu central, în funcția de erori din `main.py`, nu în fiecare endpoint. Scrierea folosește o sesiune proprie a bazei și nu poate strica răspunsul (o eventuală eroare ajunge doar în log).
- Citirile ofițerului medical din alte endpoint-uri decât tabloul și alertele (de exemplu `timeline`) primesc acțiunea `read_crew_data` (nu e în lista din contract, dar câmpul e text liber).
- La `GET /access-log` sar peste intrările de login eșuat pentru conturi inexistente: rolul lor e `unknown`, iar contractul (`AccessLogEntry.actor_role`) acceptă doar `astronaut`/`cmo`/`earth`. Ele rămân în jurnal.
- **Smoke își face baza în rădăcina repo-ului** (`Shadow/shadow.sqlite`), pentru că pornește din rădăcină. E ignorată de git. N-am mutat-o în `backend/`, ca smoke să nu șteargă baza serverului tău dacă rulează în același timp.

### De făcut de tine (git)
`backend/shadow.sqlite-shm` și `backend/shadow.sqlite-wal` au ajuns într-un commit mai vechi (sunt fișiere temporare ale bazei, se schimbă la fiecare pornire). Ca git să nu le mai urmărească (fișierele rămân pe disc):
```
git rm --cached backend/shadow.sqlite-shm backend/shadow.sqlite-wal
```

### Cum verific eu de mână
1. `cd backend; uv run uvicorn app.main:app --port 8000`
2. În /docs: „Authorize” cu `mock-medic` → `GET /api/v1/crew/cm-2/dashboard`; apoi „Authorize” cu `mock-comandant` → același endpoint (403)
3. „Authorize” cu `mock-specialist2` → `GET /api/v1/access-log` → cele două intrări, cea mai nouă prima

### Mesaj de commit propus
backend: T08 jurnalul de acces

### Următorul task
T09 (dependențele lui sunt gata: da, T02 și T05)
