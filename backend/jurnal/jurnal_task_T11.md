## T11 — Seed: istoricul zilelor 1–96

### Pe scurt, ce am făcut (pe înțeles)

La T10 am scris generatorul care inventează datele misiunii, dar le ținea doar în memorie. Acum, **la fiecare pornire a serverului**, istoricul zilelor 1–96 se scrie în baza de date, ca restul aplicației (graficele, motorul de alerte, derulatorul) să aibă de unde citi.

Ce ajunge în bază, pentru cei 4 astronauți:
- **3.072 de măsurători** (96 de zile × 4 oameni × 8 valori: puls de noapte, puls în repaus, HRV, temperatură, somn, tensiune sistolică și diastolică, glicemie);
- **384 de check-in-uri** de dimineață (96 × 4), cu numele `ck-0001`, `ck-0002`…;
- **756 de sesiuni de exerciții** (2 pe zi; lipsesc cele 4 sărite de `cm-2` în zilele 61–62), cu numele `ex-0001`…;
- **380 de sesiuni de tastare**; primele 7 zile sunt marcate „de bază” (`is_baseline`), din ele se va calcula normalul de tastare al fiecăruia (7 zile vine din `parameters.json`).

Totul e marcat `simulated`, ca să se știe că nu vine de la un senzor adevărat.

**Nimic din „viitor”:** ceasul pornește în ziua 96 la 07:00, așa că din ziua 96 intră doar ce s-a întâmplat până atunci (pulsul de noapte de la 03:00, valorile și check-in-ul de la 07:00). Exercițiile de la 09:00 și 16:00 și tastarea de la 07:15 din ziua 96 nu se scriu, pentru că încă nu au avut loc.

**Viteza:** toată pornirea durează acum **~0,5 secunde** (ținta era sub 10 s), iar consola uvicorn scrie: `SHADOW startup finished in 0.54 s`. Măsurătorile se scriu cu o singură comandă `INSERT` pentru toate rândurile, nu rând cu rând; numerele `ck-…`/`ex-…` se rezervă dintr-o dată, nu unul câte unul.

### Fișiere modificate
- `backend/app/db/seed.py` — scris `seed_history` (generează în fundal, transformă în rânduri, scrie totul o dată); sesiunile de tastare primesc și „acumulatorii” (sume) de care are nevoie T19
- `backend/app/ids.py` — funcția nouă `next_ids(session, prefix, count)`: rezervă mai multe numere dintr-o dată și scrie contorul o singură dată
- `backend/app/main.py` — la pornire se scrie istoricul (după conturi) și se afișează în consolă cât a durat pornirea
- `backend/tests/routers/test_seed_history.py` — nou, 6 teste
- `backend/tests/routers/test_ids.py` — testul de la T04 folosea prefixul `ck`, care acum are deja 384 de check-in-uri reale; l-am mutat pe un prefix de test (`tst`), fără să-l slăbesc; plus un test nou pentru `next_ids`

### Teste adăugate
- `test_cm2_has_96_checkins_and_night_pulse_every_day` — `cm-2` are 96 de check-in-uri și pulsul de noapte în fiecare zi 1–96
- `test_everything_is_marked_simulated` — toate rândurile sunt `simulated`
- `test_ids_and_counters` — primul check-in e `ck-0001`; contoarele din `sim_state` sunt egale cu numărul de rânduri
- `test_nothing_after_mission_start` — nicio valoare după ziua 96, 07:00; niciun exercițiu în ziua 96
- `test_skipped_exercise_and_keystroke_baseline` — `cm-2` nu are exerciții în ziua 61; zilele de bază ale tastării sunt 1–7; sumele se potrivesc cu mediile
- `test_startup_is_fast` — pornirea completă sub 10 s
- `tests/routers/test_ids.py::test_next_ids_reserves_a_block` — rezervarea a 3 numere dă `blk-0001…0003`, apoi următorul e `blk-0004`

### Rezultate
pytest 84 trecute / 0 picate (toată suita în ~51 s) · ruff ok · smoke OK · serverul pornit de 2 ori la rând: `SHADOW startup finished in 0.54 s` / `0.46 s`, `"db":"ok"` · în bază: 3.072 măsurători, 384 check-in-uri, 756 exerciții, 380 sesiuni de tastare · editorul: fără probleme

### Endpointuri devenite reale
niciunul (endpoint-urile încă citesc mock-ul; datele din bază le folosesc T12–T21)

### Texte rămase în română
niciunul nou

### Decizii luate singur
- **`loading_score` al exercițiilor** (stimulul osos) e obligatoriu în tabel, dar formula lui vine la T28; până atunci e `0`.
- **Nimic după ora de pornire a ceasului** (am adăugat parametrul `not_after` la `seed_history`), ca să nu existe „exerciții făcute în viitor”.
- Dacă baza nu se recreează la pornire (`RESET_DB_ON_START=false`) și există deja check-in-uri, istoricul nu se mai scrie a doua oară.
- Am adăugat `next_ids` în `app/ids.py` (fișier din T04), pentru capcana din task: fără el, ~1.100 de apeluri `next_id` ar fi încetinit pornirea.
- Măsurătorile se inserează cu `insert(Measurement)` în loc de `add_all`: o singură scriere, de ~4 ori mai rapidă (0,72 s → 0,19 s); restul rândurilor tot cu `add_all`, o singură dată.
- Linia cu durata pornirii se scrie prin logger-ul `uvicorn.error`, singurul pe care uvicorn îl afișează implicit.

### Cum verific eu de mână
1. `cd backend; uv run uvicorn app.main:app --port 8000` → în consolă: `SHADOW startup finished in 0.5 s`
2. Ctrl+C, apoi: `uv run python -c "import sqlite3; c=sqlite3.connect('shadow.sqlite'); print({t: c.execute(f'select count(*) from {t}').fetchone()[0] for t in ('measurements','checkins','exercise_sessions','keystroke_sessions')})"` → 3072 / 384 / 756 / 380
3. `uv run pytest tests/routers/test_seed_history.py -v`

### Mesaj de commit propus
backend: T11 seed: istoricul zilelor 1–96

### Următorul task
T12 (dependențele lui sunt gata: da, T05)
