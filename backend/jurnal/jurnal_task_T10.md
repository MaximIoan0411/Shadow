## T10 — Simulatorul: generatorul de scenariu

### Pe scurt, ce am făcut (pe înțeles)

Nu avem astronauți adevărați și senzori adevărați, așa că aplicația își **inventează datele**, dar după un plan precis: `data/scenario/scenario.json`. Am scris „generatorul” care, pentru fiecare zi a misiunii și pentru fiecare dintre cei 4 astronauți, produce:
- **măsurătorile zilei**: pulsul de noapte (la 03:00), pulsul în repaus, variabilitatea ritmului cardiac (HRV), temperatura, orele de somn, tensiunea (sistolică și diastolică), glicemia (la 07:00);
- **check-in-ul de dimineață** (07:00): dispoziția (de obicei 4 din 5), plus valorile pe care astronautul le-ar trece de mână;
- **exercițiile**: 2 sesiuni de forță, la 09:00 și la 16:00;
- **o sesiune de tastare** (07:15): viteza (taste pe minut), cât ține apăsată o tastă etc.

Cum le inventează:
- Fiecare astronaut are **normalul lui** (de exemplu pulsul de noapte 54 pentru `cm-2`, 61 pentru `cm-3`), scris în scenariu. Generatorul pornește de la el și adaugă un **zgomot mic**, ca valorile să nu fie identice zi de zi (la pulsul de noapte, sub 0,6 bpm, ca să nu mute zilele alertei).
- Apoi aplică **evenimentele din scenariu**: somn prost pentru toată echipa în zilele 40–41; exerciții sărite de `cm-2` în zilele 61–62; **infecția** lui `cm-2` din zilele 93–100 (pulsul de noapte crește +2, +5, +6,5, +7…, temperatura +0,4 °C, somnul −1,1 h); **tastarea mai lentă cu 18%** în zilele 95–97, deși la check-in spune „4 din 5” (decalajul de percepție); scăderea condiției cardio în zilele 110–118. Furtuna solară din ziua 97 nu se face aici (e „live”, la T25).
- E **reproductibil**: fiecare zi a fiecărui astronaut are „zarul” ei (`random.Random(seed·1000 + zi·10 + nr)`). La fiecare pornire ies **exact aceleași** date, iar ziua 94 iese la fel fie că generezi doar ziua 94, fie zilele 1–96 (important pentru saltul de zi de la T33).
- E **pur**: nu scrie nimic în baza de date; doar întoarce datele. Le scrie în bază T11.

Exemplu real, `cm-2` (normalul pulsului de noapte: 54): ziua 92 → 53,7 · ziua 93 → 55,6 · ziua 94 → 59,0 · ziua 95 → 61,0. Viteza de tastare: ~214 → 172,9 în ziua 95, cu dispoziția raportată 4.

### Fișiere modificate
- `backend/app/simulator/scenario.py` — scris generatorul (`generate` și funcțiile ajutătoare); scoase comentariile în română
- `backend/tests/engine/test_scenario.py` — nou, 12 teste

### Teste adăugate
- `test_two_runs_are_identical` — două rulări dau exact aceleași date
- `test_one_day_is_the_same_whatever_the_interval` — ziua 94 singură = ziua 94 din zilele 1–96
- `test_all_crew_every_day` — 96 de zile × 4 astronauți
- `test_infection_night_pulse_of_cm2` — pulsul lui `cm-2`: ziua 93 < normal+3, zilele 94 și 95 ≥ normal+4
- `test_night_pulse_noise_stays_small` — în afara infecției, pulsul de noapte stă la mai puțin de 0,8 bpm de normal
- `test_skipped_exercise_day_61_for_cm2` — `cm-2` nu are exerciții în ziua 61; ceilalți au 2, la 09:00 și 16:00
- `test_poor_sleep_hits_everyone` — în ziua 40 toți dorm mai puțin
- `test_keystroke_slowdown_with_mood_4` — ziua 96: tastare ≥14% mai lentă, apăsare ≥13% mai lungă, dispoziția 4
- `test_solar_storm_is_not_generated` — furtuna nu apare în istoric
- `test_times_and_units` — orele (03:00, 07:00, 07:15) și unitățile
- `test_cardio_deconditioning_raises_resting_pulse` — pulsul în repaus urcă la mijlocul zilelor 110–118 și revine după
- `test_range_is_clipped_to_mission` — cererea peste ziua 140 se oprește la 140

### Rezultate
pytest 77 trecute / 0 picate · ruff ok · smoke OK · serverul pornește · editorul: fără probleme

### Endpointuri devenite reale
niciunul (datele intră în bază și în endpoint-uri la T11 și după)

### Texte rămase în română
niciunul nou. Numele exercițiilor din sesiunile generate sunt în engleză („ARED squat”, „ARED deadlift”, „ARED heel raise”).

### Decizii luate singur
- **Condiția cardio (zilele 110–118):** scenariul dă doar `landing_readiness_min: 74`, fără cât crește pulsul sau cât scade HRV-ul. Am ales: puls în repaus până la **+6 bpm** și HRV până la **−0,3**, cu forma unui „munte” (crește spre mijlocul intervalului, apoi revine). Dacă cineva adaugă în `scenario.json` câmpurile `resting_pulse_bpm_delta` / `hrv_lnrmssd_delta`, generatorul le folosește pe acelea.
- **Zgomotul** fiecărei măsurători (de exemplu ±1,5 bpm la pulsul în repaus, ±0,1 °C la temperatură) și valorile de la exerciții (40 de minute, ~80 kg, 3 exerciții × 10 repetări) le-am ales eu, ca valori plauzibile; stau ca nume clare la începutul fișierului.
- Toate cele 8 valori zilnice intră în lista de măsurători (inclusiv tensiunea și glicemia), ca seriile pentru grafice să vină dintr-un singur loc; check-in-ul are aceleași valori, „trecute de mână”.
- Pentru a păstra o zi identică indiferent de evenimente, toate numerele aleatoare ale zilei se trag mai întâi, în aceeași ordine, iar evenimentele se aplică după.

### Cum verific eu de mână
1. `cd backend; uv run pytest tests/engine/test_scenario.py -v`
2. `uv run python -c "from app.datafiles import load_all; from app.simulator.scenario import generate; s=load_all().scenario; print([(d.day, next(v for k,v,_,_ in d.measurements if k=='night_pulse_bpm')) for d in generate(s, from_day=90, to_day=97) if d.crew_id=='cm-2'])"` → pulsul crește din ziua 93

### Mesaj de commit propus
backend: T10 simulatorul: generatorul de scenariu

### Următorul task
T11 (dependențele lui sunt gata: da, T06 și T10)
