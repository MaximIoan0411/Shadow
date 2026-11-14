## T27 — Pilonul Inima

### Pe scurt, ce am făcut (pe înțeles)

În imponderabilitate inima lucrează mai puțin și „se dezantrenează”; problema apare la revenirea în gravitație (amețeli la ridicare). Pilonul Inima dă un **scor de pregătire pentru revenire (0–100)**, comparând astronautul **cu normalul lui din zbor**, niciodată cu valorile de pe Pământ (în zbor tensiunea scade normal și pulsul nu crește).

Cum se calculează:
- **Normalul din zbor:** se ignoră primele **14 zile** (adaptarea la imponderabilitate) și ultima săptămână (cea evaluată); din zilele rămase se ia mijlocul și variația obișnuită (CV).
- **Pulsul în repaus:** dacă media pe 7 zile e peste normal + 1 × variația, **3 zile la rând** → „watch”.
- **Variabilitatea ritmului cardiac (HRV):** dacă media pe 7 zile e sub normal − 0,5 × variația → „watch”.
- **Amândouă deodată** → alertă de **nivel 2** (`cardio-2-1`, anunță ofițerul medical); **doar una** → nivel 1 (`cardio-1-1`). Toate regulile vin din `parameters.json`.
- **Scorul:** 100, minus puncte pentru pulsul peste normal, HRV-ul sub normal și o scădere a tensiunii peste prag. Se scrie zilnic în bază (`landing_readiness`), deci are grafic și apare în derulator.

Pragurile sunt **derivate** (din medicina sportivă), prezentate ca ipoteză, nu validate pe astronauți.

**Pe scenariu:** în ziua 96 toți au scorul ≥ 97 (`cm-2`: 99,2). În zilele 110–118 ale scenariului (încă în viitor), `cm-2` primește un semnal „watch” din ziua 113 și nivel 2 în zilele 116–120 (puțin după, pentru că regula folosește media pe 7 zile), cu scorul minim ~79.

**Tabloul de bord:** zona Inimii nu mai are valori fixe; arată scorul real, iar panoul ei are graficul scorului pe 10 zile.

### Fișiere modificate
- `backend/app/engine/pillars/cardio.py` — `landing_readiness` (regulile, scorul, constatarea)
- `backend/app/services/pipeline.py` — Inima în drumul datelor (live, la check-in) și în replay-ul de la pornire; scorul zilnic scris în `measurements`
- `backend/app/services/crew.py` — zona Inimii și panoul ei din date reale (graficul: scorul de pregătire)
- `backend/app/engine/derived.py` — pragurile echipei pentru Inima
- `backend/tests/engine/test_cardio.py` — nou, 9 teste

### Teste adăugate
- `test_steady_values_are_ok_and_near_100` — valori stabile → „ok”, ~100
- `test_resting_pulse_rise_for_three_days_is_watch` — puls +6 bpm mai multe zile → nivel 1
- `test_short_rise_is_not_enough` — 2 zile nu ajung
- `test_hrv_drop_alone_is_watch` — doar HRV-ul scăzut → nivel 1
- `test_both_together_is_level_2` — amândouă → nivel 2, `cardio-2-1`
- `test_systolic_drop_beyond_threshold_costs_points` — tensiunea scăzută peste prag costă 10 puncte
- `test_not_ready_in_the_first_weeks` — în primele săptămâni: „unknown”
- `test_scenario_cm2_is_ready_on_day_96_and_dips_after_110` — pe scenariu: ziua 96 ≥ 80 fără alertă; ziua 117 nivel 2
- `test_heart_pillar_on_the_dashboard` — zona Inimii și panoul ei pe date reale

### Rezultate
pytest **230 trecute / 0 picate** · ruff ok · smoke OK · pe server: Inima lui `cm-2` = 99,2 · pornirea `1.43 s`

### Endpointuri devenite reale
- zona Inimii din `GET /api/v1/crew/{crew_id}/dashboard`
- `GET /api/v1/crew/{crew_id}/pillars/cardio` (graficul scorului)

### Texte rămase în română
niciunul nou

### Decizii luate singur
- **Variația minimă**: 3% la puls și 4% la HRV, altfel la un om foarte constant zgomotul zilnic ar trece singur pragurile (am verificat pe scenariu: zero alarme false la toți, zilele 1–140).
- **Penalizările scorului**: 3 puncte pe bpm peste normal, 40 de puncte pe unitate de HRV sub normal, 10 puncte pentru tensiune scăzută peste prag. Toate în `derived.py`.
- **Simptomele de la check-in** (pentru „una + simptome → nivel 2”) nu există încă în formular; regula folosește deocamdată doar „amândouă”.
- Scorul minim al lui `cm-2` iese ~79, nu 74 cum indică scenariul (`landing_readiness_min`): media pe 7 zile netezește vârful.
- Tensiunea se compară cu normalul din zbor, nu cu cel dinainte de zbor (nu avem date dinainte).

### Cum verific eu de mână
1. `GET /api/v1/crew/cm-2/dashboard` → zona `cardio` cu scorul ~99
2. `GET /api/v1/crew/cm-2/pillars/cardio` → graficul `landing_readiness` pe 10 zile
3. `uv run pytest tests/engine/test_cardio.py -v`

### Mesaj de commit propus (comun pentru T25, T26 și T27)
backend: T25, T26, T27 radiațiile (dozimetru simulat, alerta la 2× media, adăpostul); avertizarea DONKI prin coadă cu lead_minutes; pilonul Inima cu scorul de pregătire pentru revenire

### Următoarele taskuri
T28 și T29 (dependențele lor sunt gata: da, T16)
