## T05 — Datele din data/ la pornire

### Pe scurt, ce am făcut (pe înțeles)

Folderul `data/` din rădăcina proiectului conține „cartea de reguli” a aplicației: pragurile medicale (de exemplu cu câte bătăi pe minut trebuie să crească pulsul de noapte ca să fie alertă), mediile (Marte, Lună…), catalogul de recomandări, scenariul celor 140 de zile și datele reale despre furtuna solară de la NASA.

Până acum serverul nu le citea la pornire. Acum:
- **La pornire**, serverul citește toate fișierele din `data/` și le verifică (că există, că sunt JSON corect, că au câmpurile cerute). Dacă lipsește ceva sau e greșit, serverul **nu pornește** și spune exact ce fișiere au probleme. Mai bine așa decât să pornească și să dea erori ciudate mai târziu.
- Ce a citit păstrează în memorie, în `app.state.data`, ca să nu mai citească fișierele la fiecare cerere.
- Am adăugat `get_data`: o „ușă” prin care orice endpoint sau serviciu primește aceste date (în loc să le caute singur). Exemplu: pragul NightSignal roșu este 4, citit din `parameters.json`, nu scris în cod.
- Tot la pornire se încarcă și **cheile de securitate** (`app.state.keys`), care vor semna și cripta pachetele spre Pământ. Deocamdată echipa de securitate le generează provizoriu, în memorie.
- Calea `DATA_DIR=../data` se socotește acum mereu față de folderul `backend/`, oricare ar fi folderul din care pornești serverul.

Pentru că am lucrat în `app/deps.py`, am tradus în engleză mesajele de eroare de acolo, care ajung la frontend (de exemplu „Token invalid sau expirat” → „Invalid or expired token. Please sign in again.”), și am scos comentariile în română.

### Fișiere modificate
- `backend/app/main.py` — la pornire: citește `data/` și cheile; `resolve_data_dir` pentru calea relativă; dacă datele sunt greșite, baza se închide curat
- `backend/app/deps.py` — funcția nouă `get_data`; mesajele de eroare și descrierile din Swagger traduse în engleză; comentariile în română scoase
- `backend/tests/routers/test_data_startup.py` — nou, 3 teste

### Teste adăugate
- `test_empty_data_dir_stops_startup_with_missing_files` — cu un folder `data/` gol, serverul nu pornește și eroarea numește fișierele lipsă
- `test_get_data_returns_loaded_bundle` — `get_data` dă datele încărcate; pragul `nightsignal_red_delta_bpm` este 4; cheile sunt încărcate
- `test_relative_data_dir_is_resolved_from_backend` — `../data` găsește folderul corect chiar dacă serverul e pornit din alt folder

### Rezultate
pytest 34 trecute / 0 picate · ruff ok · smoke ok · `validate_data.py` OK (169 parametri, 50 recomandări, 4 medii, 6 evenimente) · serverul pornește (`"db":"ok"`) · eroarea 401 vine în engleză · editorul: fără probleme

### Endpointuri devenite reale
niciunul (datele sunt pregătite pentru T09, T10, T12)

### Texte rămase în română
- Mesajele `DataError` (de exemplu „lipsește (căutat în …)”) vin din `app/datafiles.py`, care e contract; apar doar în consolă la pornire, nu la frontend.
- „Nu ai acces la alerta altui membru…” în `app/routers/alerts.py` (se traduce la T17).
- Exemplul din `app/schemas.py` (`ErrorResponse.message`, „Mesaj în română…”) — contract, nu l-am atins.
- Restul ca înainte: tag-urile din routere, mock-ul din `app/examples.py`, textele din `data/`, „Roluri permise” din `main.py`.

### Decizii luate singur
- Calea relativă `DATA_DIR` o socotesc față de `backend/` (cum cere taskul), nu față de folderul curent.
- Dacă citirea datelor eșuează, motorul bazei se închide totuși (`finally`), ca să nu rămână fișierul blocat.
- Am tradus mesajele din `deps.py` pentru că am lucrat în fișier (regula de limbă). Niciun test nu verifica textele vechi.
- Am adăugat al treilea test (calea relativă), necerut, dar important pentru pornirea din altă locație.

### Cum verific eu de mână
1. `cd backend; uv run uvicorn app.main:app --port 8000` → pornește normal
2. Oprești și pornești cu `$env:DATA_DIR="C:\gol"; uv run uvicorn app.main:app --port 8000` → se oprește cu lista fișierelor lipsă (apoi `Remove-Item Env:DATA_DIR`)
3. `curl.exe -s http://localhost:8000/api/v1/crew/cm-2/dashboard -H "Authorization: Bearer x"` → mesaj în engleză

### Mesaj de commit propus
backend: T05 datele din data/ la pornire

### Următorul task
T06 (dependențele lui sunt gata: da, T03 și T04)
