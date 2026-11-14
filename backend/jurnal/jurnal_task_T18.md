## T18 — Check-in și decalajul de percepție

### Pe scurt, ce am făcut (pe înțeles)

**Check-in-ul de dimineață** e formularul în care astronautul spune cum se simte (dispoziția 1–5) și trece câteva valori măsurate de mână: tensiunea, pulsul, glicemia, temperatura, orele de somn. Acum se salvează de-adevăratelea:
- **Formularul** (lista câmpurilor, cu textele „cum se măsoară / ce înseamnă / de ce contează în spațiu” și limitele) vine direct din `data/texts/checkin_indicators.json`.
- **Valorile imposibile nu blochează formularul.** Dacă cineva scrie 41,9 °C (peste limita de 41,5), acel câmp e **respins** (apare în lista `rejected`, cu motivul) și se salvează ca gol, iar restul check-in-ului se salvează normal. Răspunsul e tot 201, nu eroare.
- **„Senzor înghețat”:** dacă aceeași valoare exactă apare 3 zile la rând în check-in-urile introduse de mână, câmpul e respins ca suspect (un aparat blocat dă mereu același număr).
- **Un singur check-in pe zi:** dacă îl trimiți a doua oară în aceeași zi, îl **înlocuiește** pe primul (păstrează același număr `ck-…`).
- După salvare, valorile trec pe **drumul de la T16** (motorul + triajul), deci pot crea sau actualiza alerte; apoi se trimite evenimentul live `dashboard.changed` („checkin”).
- **Seria de zile** („Check-in saved. 96 days in a row.”): câte zile la rând, până azi, a făcut check-in, plus recordul.

**Decalajul de percepție** e ideea centrală a aplicației: astronautul spune „sunt bine”, dar datele lui obiective spun altceva.
- „Cum spune că se simte” = dispoziția × 20 (4/5 → 80 din 100).
- „Ce arată datele” = media scorurilor obiective disponibile, fiecare 0–100. **Acum** sunt două: pulsul de noapte (scorul Santinelei, T14) și somnul (100 minus 25 de puncte pentru fiecare oră sub normalul personal). Scorurile din tastare (T19) și testul de reacție (T20) se adaugă când vor exista.
- Decalajul = diferența dintre ele. **„watch”** de la 15 puncte, **„alert”** de la 25 (pragurile echipei, din `derived.py`).
- Vine cu o **explicație în cuvinte**, cu cifrele care au contat, de exemplu: „You rate yourself 4/5 (80/100); your objective data score 65/100, a little lower than how you feel (Night pulse: +7.0 bpm, Sleep: -1.1 h).”

Pentru `cm-2` în ziua 96 (dispoziția 4): datele obiective ies **65/100**, decalajul **14,8**, deci **încă „ok”**, la limită. Cu scorul tastării (T19: tastează cu 18% mai lent), decalajul va trece de 25 și va deveni „alert”, exact cum e gândit scenariul.

**Smoke** (rămas de la T17): l-am reparat cum îți recomandasem (varianta 1): înainte de exemple, smoke caută alertele reale în locul id-urilor fixe din mock.

### Fișiere modificate
- `backend/app/services/checkins.py` — scris tot: schema, validarea (imposibil / înghețat), salvarea cu înlocuire, decalajul de percepție, seria de zile, istoricul, check-in-ul de azi
- `backend/app/engine/perception_gap.py` — scris `compute` (scorurile, decalajul, starea, explicația, cauzele)
- `backend/app/routers/checkin.py` — endpoint-urile apelează serviciul (nu mai e mock); textele din Swagger în engleză
- `backend/app/services/pipeline.py` — `immune_snapshot` (scorul Santinelei pe o zi, cu aceleași reguli ca motorul); `_create` → `create_alert` (public, folosit și de smoke)
- `backend/app/engine/derived.py` — pragurile noi ale echipei: ponderile decalajului, pragul „cauză”, penalizarea somnului, cele 3 zile pentru „înghețat”
- `backend/tests/engine/test_perception_gap.py` — nou, 7 teste
- `backend/tests/routers/test_checkin_api.py` — nou, 11 teste
- `backend/tests/routers/test_alerts_api.py` — folosește `create_alert` (noul nume)
- `scripts/smoke.py` (în afara `backend/`, cu acordul tău general) — pornește aplicația (de la T07) și înlocuiește id-urile mock `al-1042` / `al-1039` cu alertele reale; diff mic (+37/−5 rânduri)

### Teste adăugate
- `test_perception_gap.py`: decalaj mare → „alert”, cu explicația exactă și cauzele în ordine; între praguri → „watch”; diferență mică → „they agree”; puțin mai jos decât senzația → „ok”, dar numește cauzele; se simte mai rău decât arată datele → „ok”; scorurile lipsă se ignoră; fără dispoziție sau fără date → „unknown”
- `test_checkin_api.py`: schema vine din `data/`; 41,9 °C → respins, restul salvat, tot 201; al doilea check-in îl înlocuiește pe primul (un singur rând, marcat „manual”); decalajul lui `cm-2` în ziua 96, cu cele două scoruri disponibile; seria de 96 de zile și mesajul; evenimentul `dashboard.changed` cu `reason = checkin`; aceeași glicemie 3 zile la rând (manual) → „frozen_sensor”; istoricul simulat nu declanșează „înghețat”; istoricul, cel mai nou primul; alt astronaut → 403

### Rezultate
pytest **153 trecute / 0 picate** · ruff ok · **smoke OK** · serverul pornit: check-in cu 41,9 °C → 201, `rejected = temperature_c / implausible`, decalaj 14,8, „Check-in saved. 96 days in a row.” · editorul: fără erori de cod (doar avertismentele cunoscute de interpretor la importuri)

### Endpointuri devenite reale
- `GET /api/v1/checkin/schema`
- `POST /api/v1/crew/{crew_id}/checkins`
- `GET /api/v1/crew/{crew_id}/checkins`
- `GET /api/v1/crew/{crew_id}/checkins/today`

### Texte rămase în română
- Textele formularului (etichete, „cum se măsoară” etc.) vin din `data/texts/checkin_indicators.json`; nu le traduc în cod.
- Mesajele mele de respingere sunt în engleză și nu repetă eticheta în română (de exemplu „41.9 is outside the possible range (34–41.5). Measure again.”; câmpul e dat separat, în `field`).

### Decizii luate singur
- **„Senzor înghețat” doar față de check-in-urile introduse de mână.** Taskul spune „aceeași valoare exactă 3 zile la rând”. În istoricul simulat, cu o zecimală, asta se întâmplă din întâmplare în ~4,6% din cazuri; la `cm-2`, temperatura e 37,3 în zilele 94, 95 și 96, deci în demo temperatura lui corectă ar fi fost respinsă. Acum compar doar cu zilele anterioare trimise manual.
- **Scorul somnului** (100 − 25 de puncte pe oră sub normal) și **ponderile egale** ale scorurilor obiective le-am ales eu; stau în `derived.py`, marcate ca alese de echipă.
- **Explicația decalajului** are cinci variante (mare, „agree”, puțin sub, puțin peste, mult peste), ca să nu spună „they agree” când diferența e aproape de prag.
- Pentru validarea valorilor imposibile folosesc `security/validation.check` (al echipei de securitate), dar fără regula ei de 20 de repetări, care e pentru dispozitive.
- Valorile din check-in pornesc motorul (temperatura și somnul ating pilonul Santinela), dar regulile lui folosesc pulsul de noapte; deci, de obicei, check-in-ul actualizează alerta existentă, nu creează una nouă.
- Istoricul simulat are deja un check-in în ziua 96 (la 07:00); check-in-ul trimis azi îl înlocuiește (și devine „manual”).
- **Greșeala mea, reparată:** în timpul T18 am trecut din neatenție `scripts/smoke.py` prin `ruff format`, care l-ar fi reformatat complet; l-am readus la versiunea din git și am pus la loc doar modificările mele.

### Cum verific eu de mână
1. `cd backend; uv run uvicorn app.main:app --port 8000` → /docs, „Authorize” cu `mock-specialist2`
2. `POST /api/v1/crew/cm-2/checkins` cu `{"mood":4,"temperature_c":41.9,"sleep_hours":5.5}` → 201, `rejected` are temperatura, `perception_gap` cu explicația
3. Trimite-l din nou cu `"mood":2` → `GET /api/v1/crew/cm-2/checkins/today` arată dispoziția 2

### Mesaj de commit propus
backend: T18 check-in și decalajul de percepție

### Următorul task
T19 (dependențele lui sunt gata: da, T16)
