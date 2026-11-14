## T29 — Semnale încrucișate + cauza de mediu

### Pe scurt, ce am făcut (pe înțeles)

Două idei:

**1. Cauza de mediu.** Dacă tot echipajul doarme prost în aceleași nopți, problema nu e în oameni, ci probabil **în cabină** (lumină, zgomot, temperatură, program). Aplicația trebuie să spună asta, nu să-i trimită pe toți la medic.

**2. Semnalele încrucișate.** Trei abateri mici, fiecare prea slabă ca să fie alertă (puls de noapte puțin mai sus, somn puțin mai scurt, tastare puțin mai lentă), venite din **piloni diferiți** la același om, în aceleași zile, cântăresc mai mult împreună.

Pentru amândouă am introdus **semnalele slabe**: abateri mici față de normalul personal, care singure nu dau alertă:
- puls de noapte cu ≥ 2 bpm peste normal; temperatură ≥ +0,3 °C; somn cu ≥ 1 h sub normal; tastare cu ≥ 8% mai lentă.

Apoi:
- **Cauza de mediu:** dacă **cel puțin 3 din 4** astronauți au **același** semnal slab **în aceeași zi**, fiecare primește o alertă de nivel 1 cu **cauza „environmental”** și explicația: „The same deviation in 4 of 4 crew members: the problem is probably in the cabin…”, plus o recomandare despre programul de lumină și somn. Rezultatul pe istoric: **în ziua 40**, toți patru primesc „Sleep changed for the whole crew (4 of 4)”.
- **Cauza individuală:** toate celelalte alerte primesc cauza „individual” („Only you have this deviation…”); de exemplu alerta imunitară a lui `cm-2`. Alertele de radiații au cauza „environmental” (furtuna, nu corpul).
- **Semnalul încrucișat:** semnalele slabe ale unui om din ultimele 3 zile, din cel puțin 2 piloni, fără cele comune întregului echipaj → un „cross signal” pe tabloul de bord, cu încrederea (0,4 + 0,1 pe semnal, maximum 0,9). Pentru `cm-2` în ziua 96: **„Possible onset of an illness”**, imunitar + tastare, încredere 0,8: puls de noapte +7, temperatură +0,4, somn −1,0 h, tastare −18%.

Ca să meargă, **replay-ul de la pornire merge acum zi cu zi pentru tot echipajul** (regulile fiecăruia → verificarea pe echipaj → reverificarea alertelor, T30), nu om cu om.

### Fișiere modificate
- `backend/app/engine/cross_signals.py` — `weak_signals`, `environmental_cause`, `environmental_finding`, `detect`
- `backend/app/services/pipeline.py` — replay-ul zi cu zi; semnalele zilnice (`observations_for_day`); `environmental_pass`; `cross_signals_for` (tabloul de bord); cauza pusă la crearea și actualizarea alertelor
- `backend/app/services/crew.py` — `cross_signals` în tabloul de bord
- `backend/app/services/radiation.py` — alertele de radiații au cauza „environmental”
- `backend/app/engine/derived.py` — pragurile semnalelor slabe și ale încrederii
- `backend/tests/engine/test_cross_signals.py` — nou, 6 teste
- `backend/tests/routers/test_keystrokes_api.py` — numără doar alertele de tastare deschise (istoricul are acum și alertele de somn din ziua 40, închise)

### Teste adăugate
- `test_weak_signal_thresholds` — pragurile semnalelor slabe
- `test_environmental_cause_needs_three_members` — 2 membri nu ajung, 3 da
- `test_cross_signal_needs_two_pillars` — un singur pilon nu ajunge; 2 piloni → „Possible onset of an illness”
- `test_day_40_crew_wide_sleep_alerts_are_environmental` — ziua 40: alerte pentru toți patru, cauza „environmental”, explicația cu „4 of 4” și „cabin”
- `test_cm2_immune_alert_is_individual` — alerta imunitară a lui `cm-2`: „individual”
- `test_cm2_has_a_cross_signal_on_day_96` — `cm-2` are semnal încrucișat (imunitar + tastare); `cm-1` nu; în ziua 40 nimeni (e cauză de mediu)

### Rezultate
pytest **247 trecute / 0 picate** · ruff ok · smoke OK · pe server: semnalul încrucișat al lui `cm-2` apare pe tabloul de bord · pornirea `1.76 s` / `1.90 s`

### Endpointuri devenite reale
- `cross_signals` și `cause` / `cause_explanation` (în alerte) în `GET /api/v1/crew/{crew_id}/dashboard` și `GET /api/v1/alerts/{alert_id}`

### Texte rămase în română
- Pașii planului pentru alertele de mediu vin din catalog (`behavioral-1-5`); nu-i traduc în cod.

### Decizii luate singur
- **Semnalele slabe** (pragurile de mai sus) sunt o noutate necesară: în scenariu, somnul prost din ziua 40 e prea mic pentru regulile existente, deci altfel nu ar fi existat nicio alertă de „mediu”. Pragurile le-am ales eu (`derived.py`).
- Alerta de mediu e de pilonul **Tastatura** pentru somn și tastare (recomandarea `behavioral-1-5`, despre programul de lumină și somn), și **Santinela** pentru puls și temperatură.
- **Cauza „de mediu” e verificată în replay (zi cu zi)**; în timpul misiunii live, verificarea pe echipaj se va face la fiecare zi nouă, când vor exista zile noi live (saltul de zi, T33).
- Pe tabloul de bord, semnalele comune echipajului (de mediu) nu intră în semnalul încrucișat.
- **Viteza:** semnalele încrucișate citesc istoricul tuturor celor 4 astronauți, așa că tabloul de bord a urcat la ~160–200 ms (ținta: ~200 ms). Dacă devine o problemă, se poate ține în memorie.

### Cum verific eu de mână
1. `GET /api/v1/crew/cm-2/dashboard` → `cross_signals`: „Possible onset of an illness”
2. `GET /api/v1/crew/cm-2/dashboard?as_of_day=40` → zona Tastatura galbenă, `cross_signals` gol; `GET /api/v1/crew/cm-2/timeline` → zilele 40–42 colorate
3. `GET /api/v1/alerts/<alerta din ziua 40>` → `cause = environmental`

### Mesaj de commit propus
(comun cu T28 și T30, vezi `jurnal_task_T30.md`)
