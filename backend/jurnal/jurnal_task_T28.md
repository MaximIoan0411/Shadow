## T28 — Pilonul Încărcarea + exerciții

### Pe scurt, ce am făcut (pe înțeles)

Fără gravitație, oasele nu mai sunt „încărcate” și pierd densitate (1–1,5% pe lună fără exerciții). Pilonul Încărcarea măsoară cât stimul primesc oasele din exercițiile de forță:
- **Scorul unei sesiuni:** repetări × greutate, dar **primele 5 repetări ale fiecărui set contează întreg**, restul doar pe jumătate (osul răspunde mai ales la primele încărcări). E scalat ca o sesiune obișnuită (3 seturi × 10 repetări × 80 kg) să dea ~33 de puncte.
- **Scorul zilei:** suma sesiunilor, **+20% dacă sunt două sesiuni la cel puțin 4 ore distanță**. O zi normală (09:00 și 16:00) dă ~80 = ținta zilnică.
- **Recomandarea de împărțire:** cât timp azi s-a făcut mai puțin de 2 sesiuni („Do a second session today, at least 4 hours after the first one.”).
- **Seria „Training in two sessions”**: câte zile la rând cu antrenamentul împărțit.
- **Proiecția pierderii osoase** (estimare, nu măsurătoare): pornește de la rata NASA cu aparatul ARED (−0,64%/lună) și se apropie de rata fără ARED (−2,17%) când aderența scade; varianta „împărțită” e presupusă puțin mai bună (×0,7). Nota spune clar că efectul împărțirii e **demonstrat doar pe animale**.
- **Endpoint-urile:** planul de azi, înregistrarea unei sesiuni (salvată „manual”, apoi `dashboard.changed`) și istoricul.

La pornire se calculează scorul tuturor sesiunilor din istoric (până acum era 0) și scorul fiecărei zile, pentru grafic. Zona „Loading” de pe tabloul de bord arată acum scorul zilei de ieri (azi e încă în desfășurare): `cm-2` are 98,1. În ziua 62 (după exercițiile sărite) zona e „watch”.

### Fișiere modificate
- `backend/app/engine/pillars/musculoskeletal.py` — `session_score`, `daily_loading`, `split_recommended`, `projection`, `score`
- `backend/app/services/exercise.py` — scris tot: planul de azi, înregistrarea, istoricul, seria, proiecția, scorurile din istoric la pornire
- `backend/app/routers/exercise.py` — endpoint-urile reale; textele în engleză
- `backend/app/services/crew.py` — zona și panoul Încărcării din date reale (graficul: scorul zilnic); seria din tabloul de bord vine din serviciul de exerciții
- `backend/app/main.py` — scorurile exercițiilor la pornire
- `backend/app/engine/derived.py` — pragurile echipei pentru încărcare
- `backend/tests/engine/test_loading.py` — nou, 7 teste

### Teste adăugate
- `test_session_score_has_diminishing_returns` — sesiunea normală = 33,3; 10 repetări = 1,5 × 5 repetări
- `test_second_session_7_hours_later_gets_the_bonus` — a doua sesiune la 7 ore → +20%; la 2 ore → fără bonus; ziua normală ≈ 80
- `test_split_recommended_on_the_skipped_day_61` — ziua 61 (sărită) → recomandarea de împărțire
- `test_projection_is_an_estimate_between_ared_and_pre_ared` — proiecția între ratele NASA, varianta împărțită mai bună, nota „doar pe animale”
- `test_score` — ținta atinsă → „ok”; sub jumătate → „watch”
- `test_today_and_logging_a_session` — planul de azi, două sesiuni înregistrate → scorul zilei ~80, nu mai e recomandată împărțirea
- `test_history_has_loading_scores_and_the_dashboard_uses_them` — istoricul are scoruri; tabloul de bord folosește scorul de ieri; ziua 62 → „watch”

### Rezultate
pytest **247 trecute / 0 picate** (împreună cu T29–T30) · ruff ok · smoke OK · pe server: zona Loading „Bone loading 78/80: on track”, 98,1

### Endpointuri devenite reale
- `GET /api/v1/crew/{crew_id}/exercise/today`, `POST /api/v1/crew/{crew_id}/exercise/sessions`, `GET /api/v1/crew/{crew_id}/exercise/sessions`
- zona și panoul `musculoskeletal` din tabloul de bord

### Texte rămase în română
niciunul nou (numele exercițiilor din istoric sunt deja în engleză)

### Decizii luate singur
- **Toate cifrele de calibrare** (5 repetări întregi, jumătate după, 33,3 puncte pe sesiune, bonus 20% la ≥ 4 h, ținta 80, factorul 0,7 pentru varianta împărțită, aderența pe 14 zile) le-am ales eu; stau în `derived.py`.
- **Alerte de forță** (`alert_strength_drop_level2/3`, scădere de 10% / 20%) nu se pot calcula încă: nu există teste de forță în date. Pilonul nu creează alerte deocamdată.
- Zona de pe tabloul de bord folosește **ziua de ieri**, ca dimineața devreme (0 sesiuni azi) să nu apară mereu „watch”.
- O sesiune înregistrată cu o oră din viitor intră pe ziua curentă.

### Cum verific eu de mână
1. Ca `mock-specialist2`: `GET /api/v1/crew/cm-2/exercise/today` → 0 sesiuni, recomandarea de împărțire
2. `POST /api/v1/crew/cm-2/exercise/sessions` de două ori, la 09:00 și 16:00 → `GET …/exercise/today` → scorul ~80

### Mesaj de commit propus
(comun cu T29 și T30, vezi `jurnal_task_T30.md`)
