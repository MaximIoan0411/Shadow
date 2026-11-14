## T15 — Motor: triajul

### Pe scurt, ce am făcut (pe înțeles)

Regulile pilonilor (de exemplu NightSignal, de la T14) spun doar „am găsit ceva”: o **constatare**, cu un nivel (1, 2 sau 3). Dar aplicația nu trebuie să creeze o alertă nouă la fiecare noapte în care pulsul e mare, altfel astronautul ar primi zece alerte pentru aceeași boală.

**Triajul** e „dispecerul” care hotărăște ce se face cu fiecare constatare, uitându-se la alertele deja deschise:
- **Nu există alertă deschisă** pe acel subiect, pentru acel astronaut → se **creează** una nouă.
- **Există, la același nivel sau mai sus** → se **actualizează** (titlul, explicația, dovezile devin cele noi), dar **nivelul rămâne**. Nivelul **nu coboară niciodată** singur: o alertă roșie nu devine galbenă doar pentru că o noapte a fost mai bună. O închide un om (astronautul sau ofițerul medical).
- **Există, dar la un nivel mai mic** → se **escaladează** la noul nivel (de exemplu galben → roșu în ziua 95 pentru `cm-2`).
- Dacă vin **două constatări pe același subiect** în același timp (de exemplu și galben, și roșu pentru imunitar), se ia **doar cea mai gravă**.

„Subiectul” e perechea (astronaut, pilon): pulsul lui `cm-2` și tastarea lui `cm-2` sunt alerte separate; la fel pulsul lui `cm-1` și cel al lui `cm-2`.

E o funcție „pură”: primește constatările și lista alertelor deschise și întoarce deciziile. Scrierea în bază o face T16.

### Fișiere modificate
- `backend/app/engine/triage.py` — scrisă funcția `decide` (plus alegerea celei mai grave constatări pe subiect); comentariul în română înlocuit cu o descriere scurtă în engleză
- `backend/tests/engine/test_triage.py` — nou, 8 teste

### Teste adăugate
- `test_no_open_alert_creates` — fără alertă deschisă → creare
- `test_open_alert_same_level_updates` — același nivel → actualizare cu textul nou
- `test_level_never_goes_down` — alertă deschisă la nivel 3, constatare nivel 1 → actualizare, nivelul rămâne 3
- `test_lower_open_alert_escalates` — alertă la nivel 1, constatare nivel 2 → escaladare la 2
- `test_two_findings_same_subject_one_decision_most_severe` — galben + roșu pe același subiect → o singură decizie, cea roșie
- `test_same_level_alert_beats_watch` — la același nivel, „alert” e mai grav decât „watch”
- `test_different_subjects_and_crew_are_separate` — subiectele și astronauții diferiți au decizii separate
- `test_no_findings_no_decisions` — fără constatări → nicio decizie (alertele deschise rămân cum sunt)

### Rezultate
`pytest tests/engine` 56 trecute · pytest total 122 trecute / 0 picate · ruff ok · smoke OK · serverul pornește · editorul: fără probleme

### Endpointuri devenite reale
niciunul (deciziile le aplică T16 în baza de date)

### Texte rămase în română
niciunul nou

### Decizii luate singur
- **„Cea mai gravă”** = nivelul mai mare; la nivel egal, „alert” înaintea „watch”; apoi ziua cea mai nouă.
- La **actualizare**, decizia poartă și nivelul alertei existente (`new_level` = nivelul care rămâne), ca T16 să nu trebuiască să-l caute din nou.
- **Lipsa unei constatări nu închide alerta** (nu există decizia „close”): închiderea o face un om, prin `/alerts/{id}/resolve`.
- Deciziile ies în ordinea în care au apărut subiectele în listă (ușor de urmărit în log-uri și teste).

### Cum verific eu de mână
1. `cd backend; uv run pytest tests/engine/test_triage.py -v`

### Mesaj de commit propus
backend: T15 motor: triajul

### Următorul task
T16 (dependențele lui sunt gata: da, T15)
