## T06 — Seed: echipaj și conturi

### Pe scurt, ce am făcut (pe înțeles)

„Seed” înseamnă datele de început pe care serverul le pune singur în baza de date când pornește. Baza se recreează goală la fiecare pornire (T03), așa că fără seed nu ar exista nici astronauți, nici conturi cu care să te autentifici.

Acum, la fiecare pornire:
- Serverul citește `backend/seed/users.json` și creează **cei 4 membri ai echipajului** (tabelul `crew`): Comandantul (`cm-1`), Specialistul de misiune 2 (`cm-2`), Ofițerul medical (`cm-3`, singurul marcat ca medic de bord) și Inginerul de zbor (`cm-4`).
- Creează apoi **cele 5 conturi** (tabelul `users`): câte unul pentru fiecare astronaut, plus contul `earth` pentru medicul de pe Pământ (care nu e în echipaj).
- **Parolele nu se salvează niciodată așa cum sunt.** Fiecare parolă trece printr-o funcție de „hash” (de la echipa de securitate), care o transformă într-un șir de caractere din care parola nu mai poate fi aflată înapoi. La login (T07), serverul va face același calcul pe parola tastată și va compara rezultatele. Dacă cineva fură baza de date, nu află parolele.
- Hash-ul e lent intenționat (ca să fie greu de ghicit parola prin încercări), așa că îl calculez „în fundal” (`asyncio.to_thread`), ca serverul să nu înghețe cât timp lucrează. Cele 5 parole se calculează în paralel.
- Echipajul se salvează **înaintea** conturilor, pentru că fiecare cont arată spre un membru al echipajului; altfel baza ar refuza legătura.

### Fișiere modificate
- `backend/app/db/seed.py` — am scris `seed_crew_and_users` (citește JSON-ul, creează echipajul, apoi conturile cu parola ca hash); am scos comentariile în română
- `backend/app/main.py` — la pornire se apelează seed-ul și se salvează (`commit`)
- `backend/tests/routers/test_seed.py` — nou, 4 teste

### Teste adăugate
- `test_seed_creates_crew_and_accounts` — 4 membri, 5 conturi; doar `cm-3` e medic de bord; contul `earth` nu are membru de echipaj
- `test_passwords_are_stored_only_as_hashes` — nicio parolă nu apare în clar în bază; hash-ul se verifică cu parola corectă și refuză una greșită
- `test_each_account_has_its_own_password` — parola lui `cm-1` nu merge pe contul lui `cm-2`
- `test_seed_is_not_repeated_when_db_is_kept` — dacă baza nu se șterge la pornire, seed-ul nu dublează conturile

### Rezultate
pytest 38 trecute / 0 picate · ruff ok · smoke ok · serverul pornește (`"db":"ok"`); în `shadow.sqlite` sunt 4 membri și 5 conturi cu hash `scrypt$...` · editorul: fără probleme

### Endpointuri devenite reale
niciunul (login-ul real vine la T07, care va folosi aceste conturi)

### Texte rămase în română
- **Numele afișate** (`display_name`) din `backend/seed/users.json`: „Comandant”, „Specialist de misiune 2”, „Ofițer medical de bord”, „Inginer de zbor”, „Medicul de zbor”. Vor ajunge la frontend după T07/T21. Taskul doar citește fișierul, așa că nu l-am modificat. **Propunere:** le traduc în engleză (Commander, Mission Specialist 2, Crew Medical Officer, Flight Engineer, Flight Surgeon) la T07, dacă ești de acord.
- Restul ca înainte (mock-ul din `app/examples.py`, tag-urile din routere, `data/`).

### Decizii luate singur
- **Titlurile rolurilor** (`role_title`) le-am pus într-o hartă mică în cod, în engleză: Commander, Mission Specialist, Crew Medical Officer, Flight Engineer.
- `is_cmo` (medicul de bord) e adevărat pentru contul cu rolul `cmo`, adică `cm-3`.
- Seed-ul nu face nimic dacă există deja conturi (cazul `RESET_DB_ON_START=false`), altfel pornirea ar da eroare de cont dublat.
- Calea spre `users.json` e socotită față de `backend/`, ca la `data/`.

### Cum verific eu de mână
1. `cd backend; uv run uvicorn app.main:app --port 8000`, apoi oprești (Ctrl+C)
2. `uv run python -c "import sqlite3; c=sqlite3.connect('shadow.sqlite'); print(c.execute('select id, display_name, role_title from crew').fetchall()); print(c.execute('select username, substr(password_hash,1,20) from users').fetchall())"` → 4 membri, 5 conturi cu `scrypt$...`
3. `uv run pytest tests/routers/test_seed.py -v`

### Mesaj de commit propus
backend: T06 seed: echipaj și conturi

### Următorul task
T07 (dependențele lui sunt gata: da, T06)
