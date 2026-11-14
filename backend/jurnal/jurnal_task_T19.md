## T19 — Tastarea

### Pe scurt, ce am făcut (pe înțeles)

Pilonul „Tastatura” se uită la **cum** tastează astronautul, nu la **ce** tastează. Când ești obosit, ții tastele apăsate mai mult și scrii mai rar, chiar dacă tu simți că ești bine. Frontend-ul trimite doar timpii apăsărilor (când a fost apăsată și eliberată fiecare tastă) și tipul tastei (literă, spațiu, backspace…); **litera nu ajunge niciodată la server**, iar în baza de date sunt doar numere.

Ce face acum backend-ul:
- **Adună loturile într-o sesiune.** Frontend-ul trimite câte un lot la ~5 secunde; loturile cu același `session_id` se adună. Din ele se calculează:
  - **cât ții o tastă apăsată** („hold”),
  - **cât trece de la o tastă la următoarea** („flight”); pauzele mai lungi de 2 secunde (te-ai oprit să te gândești) nu se numără,
  - **viteza** (taste pe minut, doar din timpul în care chiar tastezi),
  - **cât de des apeși backspace**.
  Se țin doar sume, așa că două loturi dau exact același rezultat ca un singur lot mare.
- **Normalul personal de tastare** = media primelor 7 sesiuni ale contului (cele marcate „de bază” în istoric).
- **Indicele de oboseală (0–100):** cât de mult s-a abătut sesiunea de la normalul tău, numărând doar schimbările „în direcția oboselii” (taste ținute mai mult, viteză mai mică, pauze mai lungi, mai multe corecturi). Dacă tastezi mai repede ca de obicei, indicele rămâne 0. De la **50** starea e „watch”, de la **75** „alert”. O sesiune e judecată abia după **30 de taste** (primele câteva taste sunt prea puține ca să spună ceva).
- **Alerta:** când o sesiune trece pragul, datele merg pe drumul de la T16 și motorul creează (sau actualizează) alerta de tastare, de nivel 1, cu recomandarea `behavioral-1-1`. Evenimentele live (`alert.created`, `dashboard.changed`) pleacă o singură dată, la trecerea pragului, nu la fiecare lot.
- **La pornire**, regula se rulează și peste istoric. Rezultatul, exact ca în scenariu: `cm-2` tastează cu **18% mai lent** din ziua 95 → alerta **„Typing 18% slower than usual”** (`al-0002`, nivel 1, „watch”, indice de oboseală 72). Somnul prost al întregului echipaj din zilele 40–41 (tastare −10%) dă cel mult 36, deci **nu** creează alerte; zilele normale dau cel mult 10.
- **Decalajul de percepție (T18) primește scorul tastării** (100 − indicele de oboseală). Pentru `cm-2` în ziua 96, cu dispoziția 4/5: datele obiective scad la ~53/100, decalajul trece de **25** și starea devine **„alert”**: „spune că e bine, dar tastează cu 18% mai lent și pulsul de noapte a crescut”. Asta e ideea centrală a demo-ului.
- **Rezumatul** (`GET …/keystrokes/summary`): normalul personal, sesiunea curentă și ultimele sesiuni, pentru cardul „Your rhythm”.

### Fișiere modificate
- `backend/app/engine/pillars/behavioral.py` — `accumulate` (adunarea loturilor), `typing_baseline`, `fatigue_index`, `status_for`, `typing_finding` (constatarea, în engleză), `score`; funcțiile PVT rămân schelet pentru T20
- `backend/app/services/behavioral.py` — scris: primirea unui lot (`add_batch`), rezumatul, scorul tastării pentru decalajul de percepție
- `backend/app/routers/behavioral.py` — endpoint-urile de tastare apelează serviciul; textele fișierului în engleză (cele două endpoint-uri PVT rămân mock până la T20)
- `backend/app/services/pipeline.py` — regula de tastare legată în drumul datelor și în replay-ul de la pornire; la actualizare, culoarea alertei poate urca la „alert”
- `backend/app/db/repos.py` — trei citiri noi pentru sesiunile de tastare
- `backend/app/services/checkins.py` — decalajul de percepție folosește și scorul tastării
- `backend/app/engine/derived.py` — pragurile echipei pentru indicele de oboseală
- `backend/tests/engine/test_keystrokes.py` — nou, 13 teste
- `backend/tests/routers/test_keystrokes_api.py` — nou, 9 teste
- `backend/tests/routers/test_alerts_api.py`, `test_checkin_api.py` — folosesc alerta reală de tastare (nu una creată de test); testul decalajului cere acum „alert”, cum prevedea T18
- `scripts/smoke.py` (în afara `backend/`) — am scos alerta de test de la T18: smoke ia acum ambele alerte reale direct din API (diff total față de git: +16/−5 rânduri)

### Teste adăugate
- `test_keystrokes.py` (motor): trăsăturile unei sesiuni constante; **două loturi = un lot**; evenimente neordonate în lot; **pauza de 5 s nu intră în flight**; resetarea cronometrului între loturi; normalul și variația minimă; identic cu normalul → 0; tastarea mai rapidă nu e oboseală; **sesiunea cu 20% mai lentă are indicele vizibil mai mare**; pragurile de stare; constatarea („Typing 18% slower than usual”, nivel 1); scorul; calibrarea pe scenariu (doar `cm-2` în zilele 95–97 e „watch”)
- `test_keystrokes_api.py`: alerta lui `cm-2` creată de replay în ziua 95; sesiunile din istoric sunt judecate, cele de bază nu; loturile se adună și sesiunile scurte nu sunt judecate; o sesiune lentă creează alerta și trimite evenimentele o singură dată; o sesiune lentă actualizează alerta deja deschisă; sesiunea altui cont e refuzată (403); caracterele și id-urile prea lungi dau 422; rezumatul; tabelul nu are nicio coloană pentru text tastat

### Rezultate
pytest **175 trecute / 0 picate** · ruff ok · **smoke OK** · serverul pornit de 2 ori la rând: `SHADOW startup finished in 1.21 s` / `1.12 s` · pe server: alertele lui `cm-2` = `al-0001` (immune, nivel 2) și `al-0002` (behavioral, nivel 1, „Typing 18% slower than usual”); rezumatul arată sesiunea din ziua 95 cu 172,9 taste/min, oboseală 72,4, „watch” · în tabelul `keystroke_sessions` singurele coloane text sunt `session_id`, `crew_id`, `context`, `status` · editorul: fără probleme

### Endpointuri devenite reale
- `POST /api/v1/crew/{crew_id}/keystrokes/batches`
- `GET /api/v1/crew/{crew_id}/keystrokes/summary`

### Texte rămase în română
- Pașii planului alertei de tastare vin din `data/catalog/recommendations.json` (`behavioral-1-1`); nu-i traduc în cod.
- Titlul, explicația și dovezile alertei de tastare sunt în engleză.

### Decizii luate singur
- **Calibrarea indicelui de oboseală** (toate în `engine/derived.py`, marcate ca alese de echipă): ponderi 40% timpul de apăsare, 40% viteza, 10% pauzele dintre taste, 10% backspace; o abatere ponderată de 5 „variații personale” dă 100; o singură trăsătură poate conta cel mult cât 6 variații; variația minimă: 6 ms la apăsare, 15 ms între taste, 0,02 la backspace (cea de 8 taste/min exista deja). Le-am ales și le-am **verificat pe scenariu**, ca −18% să iasă „watch” (72), iar −10% de la somnul prost să rămână „ok” (≤ 36).
- **O sesiune e judecată abia după 30 de taste**; până atunci starea e „unknown”.
- **Alerta de tastare e mereu de nivel 1**; la un indice ≥ 75 se schimbă doar culoarea („alert”). Nivelul 2 la acest pilon ține de testul de reacție (T20).
- **Evenimentele pleacă doar la schimbarea stării** sesiunii (altfel frontend-ul ar primi `alert.updated` la fiecare 5 secunde).
- **Scorul pilonului = 100 − indicele de oboseală.** Pentru decalajul de percepție se ia ultima sesiune judecată de azi sau de ieri. Atenție la demo: dacă cineva tastează live, normal, înainte de check-in, acea sesiune devine „ultima” și decalajul scade (am văzut asta la verificarea de mână: decalaj 9,4 după o sesiune live normală).
- **În replay, alerta de tastare are ora sfârșitului sesiunii** (07:17 în ziua 95), nu 07:00.
- Am atins și fișiere în afara listei din task (`pipeline.py`, `repos.py`, `checkins.py`, `derived.py`), pentru că pasul 4 cere ca tastarea să treacă prin drumul datelor, iar T18 cerea scorul tastării în decalaj.
- Un `session_id` folosit deja de alt cont → 403; unul mai lung de 64 de caractere → 422.
- Trei așteptări din testele mele noi erau ghicite greșit (19% în loc de 18%, 33% în loc de 32%, minutul 16 în loc de 17); am corectat testele, nu codul.

### Cum verific eu de mână
1. `cd backend; uv run uvicorn app.main:app --port 8000` → /docs, „Authorize” cu `mock-specialist2`
2. `GET /api/v1/crew/cm-2/alerts` → `al-0001` (immune) și `al-0002` „Typing 18% slower than usual”
3. `GET /api/v1/crew/cm-2/keystrokes/summary?last=3` → ultima sesiune: 172,9 taste/min, `fatigue_index` 72,4, `watch`
4. `POST /api/v1/crew/cm-2/checkins` cu `{"mood":4,"sleep_hours":5.5}` → `perception_gap.status = "alert"`

### Mesaj de commit propus
backend: T19 tastarea

### Următorul task
T20 (dependențele lui sunt gata: da, T19)
