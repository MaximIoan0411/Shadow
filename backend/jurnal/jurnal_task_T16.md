## T16 — Drumul unei date + replay la pornire

### Pe scurt, ce am făcut (pe înțeles)

Până acum aveam piesele separate: regula NightSignal (T14), care spune „am găsit ceva”, și triajul (T15), care hotărăște „creez / actualizez / escaladez”. Acum le-am legat într-un **singur drum**, prin care trece orice dată nouă:

1. Vine o dată nouă (de exemplu pulsul de noapte al lui `cm-2`).
2. Se rulează **doar regulile pilonului atins** (pulsul de noapte → Santinela). Pentru restul pilonilor regulile încă nu există; vin la T19, T27, T28.
3. Se citesc alertele deja deschise ale astronautului.
4. Triajul hotărăște ce se face.
5. Se scrie în baza de date:
   - **alertă nouă**: primește un nume (`al-0001`), starea „active”, recomandarea din catalog, **planul de acțiune** (pașii recomandării), data de reverificare (peste 1–3 zile, din catalog) și o primă intrare în istoric: „created” de „SHADOW”;
   - **actualizare**: titlul, explicația și dovezile devin cele noi, nivelul rămâne;
   - **escaladare**: nivelul crește, starea devine „escalated”, iar în istoric apare „escalated” de „SHADOW”. Dacă recomandarea se schimbă (de la galben la roșu), **se schimbă și planul**: din „completează jurnalul de simptome” în „anunță ofițerul medical”.
6. Se pregătesc **evenimentele live** pentru frontend (`alert.created`, `alert.updated`, `dashboard.changed`), dar nu se trimit aici: le trimite cine apelează, **după** ce salvarea a reușit.

**Replay la pornire:** când pornește serverul, după ce istoricul zilelor 1–96 e în bază (T11), drumul de mai sus se rulează **zi cu zi**, de la ziua 1 la 96, pentru toți cei 4 astronauți, ca și cum datele ar fi venit atunci. Așa, **alerta lui `cm-2` nu mai e scrisă de mână: o produce motorul**:
- ziua 94 → NightSignal găsește +5 bpm → se **creează** alerta galbenă;
- ziua 95 → a doua noapte ≥ +4 → se **escaladează** la roșu (nivel 2), cu planul `immune-2-1`;
- ziua 96 → se actualizează: „Night pulse +7 bpm, 3 nights in a row”.

Ceilalți trei astronauți nu au nicio alertă imunitară. Toată pornirea durează **~1,1 secunde**.

### Fișiere modificate
- `backend/app/services/pipeline.py` — scrise `process` (drumul unei date) și `replay_history` (la pornire), plus crearea, actualizarea și escaladarea alertelor; scoase comentariile în română
- `backend/app/main.py` — la pornire, după istoric, se rulează replay-ul
- `backend/tests/routers/test_pipeline_replay.py` — nou, 5 teste
- `backend/tests/routers/test_ids.py` — trei teste de la T04 foloseau prefixul `al`, care acum are o alertă reală (`al-0001`); le-am mutat pe prefixe de test (`ta`, `tb`), cu aceleași verificări (la fel ca la T11)

### Teste adăugate
- `test_cm2_immune_alert_created_day_94_escalated_day_95` — o singură alertă imunitară pentru `cm-2`: creată în ziua 94, escaladată în ziua 95 (ambele de „SHADOW”), nivel 2, recomandarea `immune-2-1` cu pașii ei, dovezile puls/temperatură/somn, titlul „Night pulse +7 bpm, 3 nights in a row”
- `test_no_other_crew_has_an_immune_alert` — doar `cm-2` are alertă imunitară
- `test_process_creates_alert_and_returns_events` — un puls mare pentru `cm-1` → alertă nouă de nivel 1 și evenimentele `alert.created` + `dashboard.changed` (întoarse, nu trimise)
- `test_process_updates_existing_alert` — încă o rulare pentru `cm-2` → actualizare, nu alertă dublată
- `test_unrelated_metric_runs_no_rules` — glicemia nu atinge niciun pilon cu reguli → nimic

### Rezultate
pytest 127 trecute / 0 picate · ruff ok · smoke OK · serverul pornit de 2 ori la rând: `SHADOW startup finished in 1.21 s` / `1.04 s` · în bază: `al-0001`, `cm-2`, immune, nivel 2, escalated, ziua 94, `immune-2-1`, reverificare 2027-04-16 07:00 · editorul: fără probleme

### Endpointuri devenite reale
niciunul încă: endpoint-urile de alerte citesc mock-ul până la T17 (de aceea, deocamdată, frontend-ul vede tot alerta mock `al-1042`, iar în bază există `al-0001`)

### Texte rămase în română
- **Pașii planului** (de exemplu „Culcă-te cu o oră mai devreme în următoarele 3 nopți.”) vin din `data/catalog/recommendations.json`; conform regulii, nu-i traduc în cod.
- Titlurile, explicațiile, dovezile și nota din istoric („Escalated automatically to level 2.”) sunt în engleză.

### Decizii luate singur
- **Ora evaluării în replay**: 07:00 a fiecărei zile (după noapte, la ora check-in-ului). „Acum” se dă ca parametru; ceasul nu se mută.
- **Zilele excluse din normal**: cât timp e deschisă o alertă imunitară, zilele de la crearea ei încoace nu intră în calculul normalului (altfel boala ar deveni „normalul”).
- **La escaladare cu recomandare nouă, planul se înlocuiește** cu pașii noii recomandări, iar data de reverificare se recalculează. Pașii bifați din planul vechi se pierd (era alt plan).
- **Cauza** alertei („individual / environmental”) rămâne `unknown` până la T29, care o analizează.
- `process` și `replay_history` au primit parametri în plus (`data`, `at`, `reason`), pentru că au nevoie de praguri, catalog și ora evaluării. `dashboard.changed` se adaugă doar când apelantul dă un `reason` (check-in, tastare etc.), cum cere contractul (`{"reason": …}`).
- Pentru viteză, la replay seriile fiecărui astronaut se citesc **o singură dată** și se taie pe zile în memorie; regulile sunt exact aceleași ca la datele live.
- Replay-ul nu rulează dacă există deja alerte (cazul `RESET_DB_ON_START=false`), ca să nu dubleze istoricul.
- Nivelul 3 (pachet spre Pământ) are un `TODO T23` în cod; acum nicio regulă nu dă nivel 3.

### Cum verific eu de mână
1. `cd backend; uv run uvicorn app.main:app --port 8000` → în consolă `SHADOW startup finished in ~1 s`
2. Ctrl+C, apoi: `uv run python -c "import sqlite3; c=sqlite3.connect('shadow.sqlite'); print(c.execute('select id, crew_id, level, state, mission_day, title from alerts').fetchall()); print(c.execute('select at, action from alert_history').fetchall())"`
3. `uv run pytest tests/routers/test_pipeline_replay.py -v`

### Mesaj de commit propus
backend: T16 drumul unei date + replay la pornire

### Următorul task
T17 (dependențele lui sunt gata: da, T16)
