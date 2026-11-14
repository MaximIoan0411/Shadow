## T12 — Motor: baseline-ul personal

### Pe scurt, ce am făcut (pe înțeles)

Ideea de bază a aplicației: **fiecare astronaut e comparat cu el însuși**, nu cu valori „normale” din manualele medicale. Un puls de noapte de 61 e perfect normal pentru `cm-3`, dar pentru `cm-2`, care are de obicei 54, înseamnă că ceva nu e în regulă.

Am scris funcția care calculează acest **„normal personal”** (baseline-ul) dintr-o serie de valori:
- **Mijlocul (mediana):** valoarea din mijloc, după ce le pui în ordine. Spre deosebire de medie, o singură noapte ciudată (de exemplu 75 bpm o dată) nu o mută.
- **Cât variază de obicei („spread”):** cât se abat de obicei valorile de la mijloc, calculat tot „robust” (MAD × 1,4826), ca să nu-l strice valorile extreme. Dacă valorile sunt aproape identice, se folosește un minim (dat din afară), ca orice mică schimbare să nu pară o alarmă.
- **Zilele în alertă se scot:** altfel, dacă cineva e bolnav o săptămână, boala ar deveni „normalul” lui și alerta ar dispărea.
- **Fereastră:** se pot lua doar ultimele N zile (normalul se poate schimba în timpul zborului).
- **„Gata” sau nu:** cu prea puține valori (de exemplu sub 7 nopți), baseline-ul nu e încă de încredere (`ready = false`).
- A doua funcție, `deviation`, spune cât de departe e o valoare nouă de normal, în „unități personale”: de exemplu +3,5 înseamnă de 3,5 ori variația obișnuită a acelui om.

Exemplu real pe datele simulate: normalul pulsului de noapte al lui `cm-2`, fără zilele de boală, iese **53,9 ± 0,44 bpm** din 93 de nopți (în scenariu: 54).

E o funcție „pură”: primește numere, întoarce numere, fără bază de date și fără ceas. Pragurile (câte nopți minim, spread-ul minim) le primește ca parametri; nu sunt scrise în ea.

### Fișiere modificate
- `backend/app/engine/baseline.py` — scris `compute` și `deviation`; scos comentariile în română
- `backend/tests/engine/test_baseline.py` — nou, 11 teste

### Teste adăugate
- `test_constant_values_use_min_spread` — valori identice → se folosește spread-ul minim
- `test_robust_spread_is_scaled_mad` — spread = 1,4826 × MAD
- `test_isolated_spike_does_not_move_median` — o noapte de 75 bpm nu mută mediana
- `test_excluded_days_do_not_count` — zilele în alertă nu intră
- `test_window_keeps_only_last_days` — doar ultimele N zile
- `test_window_counts_from_last_day_even_when_it_is_excluded` — fereastra se socotește de la ultima zi, chiar dacă aceea e exclusă
- `test_ready_from_min_n` — 6 nopți: nu e gata; 7: e gata
- `test_empty_series` — serie goală: mediana necunoscută, nu e gata
- `test_deviation_in_personal_spreads` — 61 față de 54 ± 2 → +3,5
- `test_deviation_without_baseline_is_nan` — fără baseline, abaterea e „necunoscută”, nu un număr inventat
- `test_cm2_history_baseline_is_personal` — pe istoricul simulat, fiecare astronaut are alt normal, aproape de cel din scenariu

### Rezultate
`pytest tests/engine` 36 trecute · pytest total 95 trecute / 0 picate · ruff ok · smoke OK · serverul pornește · editorul: fără probleme · `baseline.py` importă doar biblioteca standard și `engine/types.py`

### Endpointuri devenite reale
niciunul (motorul îl folosesc T14, T19, T21…)

### Texte rămase în română
niciunul nou

### Decizii luate singur
- **Fereastra „ultimele N zile”** se socotește de la cea mai nouă zi din serie (inclusiv dacă acea zi e exclusă ca fiind în alertă), adică de la „acum”, nu de la ultima zi normală.
- `deviation` întoarce „necunoscut” (`NaN`) când nu există baseline sau spread-ul e 0, în loc să împartă la zero.
- Taskul îmi spunea să citesc `engine/derived.py` (`MIN_SPREAD`); nu l-am importat aici, pentru că spread-ul minim vine ca parametru (îl vor da apelanții, T14 etc.).

### Cum verific eu de mână
1. `cd backend; uv run pytest tests/engine/test_baseline.py -v`

### Mesaj de commit propus
backend: T12 motor: baseline-ul personal

### Următorul task
T13 (dependențele lui sunt gata: da, T11)
