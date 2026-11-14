## T14 — Pilonul Santinela (NightSignal)

### Pe scurt, ce am făcut (pe înțeles)

„Santinela” e pilonul care încearcă să prindă o **boală înainte să apară simptomele**. Se bazează pe un studiu real (NightSignal, Alavi et al. 2022): când corpul începe să lupte cu o infecție, **pulsul din timpul nopții crește** cu câteva bătăi pe minut, de obicei cu o zi sau două înainte să te simți rău.

Am scris regula, comparând pulsul de noapte cu **normalul personal** al astronautului (mediana nopților de dinainte, de la T12):
- **Galben (nivel 1, „watch”)** — în ultima noapte pulsul a fost cu **cel puțin 3 bpm** peste normal. Recomandarea `immune-1-1`: completează jurnalul de simptome și remăsoară noaptea următoare.
- **Roșu (nivel 2, „alert”)** — **două nopți la rând** cu **cel puțin 4 bpm** peste normal. Recomandarea `immune-2-1`: anunță ofițerul medical de bord.
- **Nimic** — dacă pulsul e în limite, dacă lipsește noaptea de azi, sau dacă baseline-ul nu e gata (mai puțin de 7 nopți).

Toate cifrele (3, 4, 2 nopți, 7 nopți) vin din `data/parameters.json`, nu sunt scrise în cod.

Fiecare constatare vine cu un **titlu gata de afișat** (de exemplu „Night pulse +7 bpm, 3 nights in a row”), o **explicație** și **dovezile**: pulsul de noapte, temperatura și somnul, fiecare cu valoarea și cât se abate de la normal.

Pe datele din scenariu iese exact cum trebuie pentru `cm-2`: ziua 93 → nimic, **ziua 94 → galben**, **ziua 95 → roșu**, ziua 96 → roșu, 3 nopți la rând.

Plus două lucruri cerute de task:
- **Scorul pilonului** (0–100, pentru corpul interactiv): 100 = ca de obicei; scade cu 6 puncte pentru fiecare bpm peste normal (exemplu: +7 bpm → 58).
- **Indicele de stres** (0–100): o medie ponderată din oboseala la tastare (50%), zilele de izolare (20%) și doza de radiații față de normal (30%). Dacă o parte lipsește, se calculează din celelalte.

### Fișiere modificate
- `backend/app/engine/pillars/immune.py` — scrise `night_signal`, `stress_index`, `score`, plus `baseline_before` (normalul din nopțile de dinainte) și `evidence` (dovezile); textele sunt în engleză
- `backend/app/engine/derived.py` — adăugate pragurile alese de echipă pentru indicele de stres și scor; comentariile traduse scurt în engleză (nu le-am șters, pentru că documentează pragurile)
- `backend/tests/engine/test_immune.py` — nou, 12 teste

### Teste adăugate
- `test_calm_night_gives_nothing` — +1 bpm → nimic
- `test_one_night_plus_4_is_yellow` — o noapte +4 → galben, `immune-1-1`
- `test_one_night_plus_3_is_yellow` — o noapte +3 → galben
- **`test_nightsignal_red_after_two_nights`** — două nopți +4 → roșu, `immune-2-1`, cu dovezile puls, temperatură, somn (testul cerut pentru ecranul Evidence)
- `test_3_9_then_4_is_not_red` — +3,9 apoi +4 → doar galben
- `test_red_needs_consecutive_nights` — +4, normal, +4 → doar galben (nu sunt la rând)
- `test_three_nights_in_a_row_title` — titlul „Night pulse +7 bpm, 3 nights in a row”
- `test_baseline_not_ready_gives_none` — doar 5 nopți de normal → nimic
- `test_missing_tonight_gives_none` — lipsește noaptea de azi → nimic
- `test_scenario_cm2_yellow_on_94_red_on_95` — pe scenariu: 93 nimic, 94 galben, 95 roșu, 96 roșu cu 3 nopți
- `test_stress_index_bounds_and_missing_parts` — indicele stă între 0 și 100 și merge și când lipsesc părți
- `test_score` — 100 când e liniște; 58 la +7 bpm; „unknown” când baseline-ul nu e gata

### Rezultate
`pytest tests/engine/test_immune.py` 12 trecute · pytest total 114 trecute / 0 picate · ruff ok · smoke OK · serverul pornește · editorul: fără probleme · `immune.py` importă doar biblioteca standard și motorul (`types`, `derived`, `baseline`)

### Endpointuri devenite reale
niciunul (regula o folosesc triajul, T15, și drumul datelor, T16)

### Texte rămase în română
niciunul nou. Titlurile, explicațiile și dovezile sunt în engleză (regula de limbă are prioritate față de task, care cerea română).

### Decizii luate singur
- **Ponderile indicelui de stres** (50% oboseală, 20% izolare, 30% doză) și scalele lor (izolare „maximă” la 140 de zile, doză „maximă” la de 6 ori normalul) **le-am ales eu**; taskul cerea „o combinație simplă, documentată”. Stau în `derived.py`, marcate ca alese de echipă.
- **Penalizarea scorului**: 6 puncte pe bpm peste normal; tot în `derived.py`.
- Funcția `night_signal` are acum câțiva parametri opționali în plus (temperatura și somnul, cu normalul lor), ca să poată construi dovezile cerute; cei vechi au rămas neschimbați.
- Normalul se calculează doar din nopțile **de dinainte** de cea evaluată (`baseline_before`); zilele în alertă le exclude apelantul (T16), care știe ce alerte există.
- Pentru scor folosesc pragul minim de variație din `derived.MIN_SPREAD` (1,5 bpm), cum era deja hotărât de echipă.

### Cum verific eu de mână
1. `cd backend; uv run pytest tests/engine/test_immune.py -v`

### Mesaj de commit propus
backend: T14 pilonul santinela (nightsignal)

### Următorul task
T15 (dependențele lui sunt gata: da, T14)
