## T20 — Testul de reacție (PVT-B)

### Pe scurt, ce am făcut (pe înțeles)

PVT-B e un test de 3 minute: pe ecran apare din când în când un semnal, iar astronautul apasă cât poate de repede. E cel mai sigur mod cunoscut de a măsura oboseala, chiar și atunci când omul simte că e odihnit. Testul rulează în frontend; la final, frontend-ul trimite toate încercările, iar backend-ul calculează rezultatul:
- **viteza medie de reacție** (media lui 1000 / timpul de reacție, în „reacții pe secundă”),
- **lapsusurile**: răspunsurile de **355 ms sau mai lente** și semnalele la care nu a răspuns deloc,
- **pornirile false** (a apăsat înainte de semnal); ele nu intră în timpii de reacție.

**Normalul personal:** primele **3 teste** ale fiecărui cont sunt de **antrenament** (oamenii se îmbunătățesc la început) și nu contează. Normalul se face din testele de după, de la al doilea încolo. Deci al 6-lea test e primul judecat.

**Judecata:** dacă viteza scade cu cel puțin **1,24 „variații personale”** față de normal (pragul de „schimbare sigură” din `parameters.json`), testul e „watch” și motorul creează sau actualizează **alerta de nivel 1 a pilonului Tastatura** (aceeași ca la tastare, `behavioral-1-1`), de exemplu „Reaction speed 10% below your baseline”.

Rezultatul PVT intră și în **decalajul de percepție** (T18) și în **scorul pilonului** de pe corp (T21).

### Fișiere modificate
- `backend/app/engine/pillars/behavioral.py` — `pvt_summary`, `pvt_baseline`, `pvt_finding`
- `backend/app/services/behavioral.py` — salvarea testului, istoricul, scorul PVT pentru decalaj
- `backend/app/routers/behavioral.py` — `POST/GET …/pvt` nu mai sunt mock
- `backend/app/services/pipeline.py` — poate primi o constatare gata făcută (cea PVT); regula de tastare rulează doar când se schimbă tastarea
- `backend/app/services/checkins.py` — decalajul de percepție folosește și scorul PVT
- `backend/app/engine/derived.py` — 2 teste minime pentru normal, variația minimă a vitezei (0,15/s)
- `backend/tests/engine/test_pvt.py` — nou, 5 teste

### Teste adăugate
- `test_lapse_at_exactly_355_ms` — 354,9 ms nu e lapsus, 355 ms este
- `test_no_answer_is_a_lapse_and_false_starts_are_not_reaction_times` — lipsa răspunsului e lapsus; pornirile false nu intră în medie
- `test_baseline_needs_two_tests_and_has_a_minimum_spread` — normalul are nevoie de 2 teste
- `test_finding_only_past_reliable_change` — sub prag nimic; peste prag „watch”, nivel 1, `behavioral-1-1`
- `test_practice_then_baseline_then_slow_test_is_watch` — 3 de antrenament + 2 pentru normal nu sunt judecate; al 6-lea normal → „ok”; unul lent → „watch”, 2 lapsusuri și alerta de tastare actualizată

### Rezultate
pytest **191 trecute / 0 picate** (împreună cu T21) · ruff ok · smoke OK · pe server: `POST /crew/cm-2/pvt` → `pvt-0001`, 201

### Endpointuri devenite reale
- `POST /api/v1/crew/{crew_id}/pvt`
- `GET /api/v1/crew/{crew_id}/pvt`

### Texte rămase în română
niciunul nou

### Decizii luate singur
- **Antrenament = 3 teste** (valoarea mai mare din `pvt_practice_runs` = [2, 3]).
- **Normalul din minimum 2 teste**, cu variația minimă 0,15/s (altfel, două teste aproape identice ar face orice abatere „uriașă”). În `derived.py`.
- `at` (ora testului) e ora misiunii de la server, nu `started_at` trimis de client.
- Rezultatul PVT nu are încă istoric simulat (nu e în scenariu), deci până nu face cineva teste, scorul PVT lipsește și nu contează.
- PVT și tastarea împart aceeași alertă (pilonul Tastatura); când PVT-ul o actualizează, titlul devine cel al PVT-ului.

### Cum verific eu de mână
1. /docs, „Authorize” cu `mock-specialist2` → `POST /api/v1/crew/cm-2/pvt` de 6 ori (primele 5 → `unknown`, al 6-lea → `ok` sau `watch`)
2. `GET /api/v1/crew/cm-2/pvt` → istoricul, cel mai nou primul

### Mesaj de commit propus
(comun cu T21, vezi `jurnal_task_T21.md`)
