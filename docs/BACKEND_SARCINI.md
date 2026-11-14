# Backend — ce trebuie implementat

**Folder:** `backend/` · **Echipa:** 2 oameni · **Unelte:** Python 3.12, uv, FastAPI, Pydantic, SQLAlchemy peste SQLite, pytest

Backend-ul este creierul aplicației: ține datele fiecărui astronaut, calculează normalul lui personal, decide
alertele și nivelul lor, mișcă mesajele între navă și Pământ și simulează misiunea. Frontend-ul doar afișează ce
calculează backend-ul.

**De unde pornești:** scheletul din `shadow-contract.zip` are deja toate cele 57 de endpoint-uri, cu date mock.
Munca ta este să înlocuiești, pe rând, corpul fiecărei funcții cu logica reală. **Calea, parametrii și modelele nu
se schimbă.** Referința completă: `contract/README.md`.

**Priorități:** `P0` = fără el nu merge demo-ul · `P1` = intră în demo dacă e gata până la ora 16 · `P2` = bonus.

## Cuprins

1. [Fundația](#1-fundația-p0-orele-02)
2. [Conturi și autentificare](#2-conturi-și-autentificare-p0)
3. [Misiune, medii, ceas](#3-misiune-medii-ceas-p0)
4. [Simulatorul misiunii](#4-simulatorul-misiunii-p0)
5. [Baseline-ul personal](#5-baseline-ul-personal-p0)
6. [Pilonul 1 — Tastatura](#6-pilonul-1--tastatura-p0)
7. [Pilonul 2 — Inima](#7-pilonul-2--inima-p1)
8. [Pilonul 3 — Santinela](#8-pilonul-3--santinela-p0)
9. [Pilonul 4 — Încărcarea](#9-pilonul-4--încărcarea-p1)
10. [Check-in și decalajul de percepție](#10-check-in-și-decalajul-de-percepție-p0)
11. [Triajul și alertele](#11-triajul-și-alertele-p0)
12. [Tabloul de bord, panourile, derulatorul](#12-tabloul-de-bord-panourile-derulatorul-p0)
13. [Coada navă ↔ Pământ](#13-coada-navă--pământ-p0)
14. [Radiații și furtuna solară](#14-radiații-și-furtuna-solară-p1)
15. [Evenimente live](#15-evenimente-live-p0)
16. [Medicul AI: puntea](#16-medicul-ai-puntea-p1)
17. [Dovezi, jurnal, demo](#17-dovezi-jurnal-demo-p1)
18. [Împărțirea între cei doi](#18-împărțirea-între-cei-doi)
19. [Cu cine te legi](#19-cu-cine-te-legi)
20. [Scheletul gol](#20-scheletul-gol)

---

## 1. Fundația (P0, orele 0–2)

Fără acestea nu poate începe nimic altceva.

| Ce | Fișier | Detalii | Gata când |
|---|---|---|---|
| Proiectul uv | `pyproject.toml`, `uv.lock` | comenzile de trecere sunt în `STRUCTURA_REPO.md`, secțiunea 10 | `uv run uvicorn app.main:app` pornește mock-ul |
| Setările | `app/config.py` | citește `.env`: `JWT_SECRET`, `TIME_SCALE`, `DATABASE_URL`, `DATA_DIR`, `AI_URL` | nicio valoare scrisă direct în cod |
| **Ceasul misiunii** | `app/clock.py` | `SimClock.now()`, `mission_day()`, `set_scale()`, `jump_to_day()` | **nicăieri în cod nu apare `datetime.now()`** |
| Baza de date | `app/db/session.py`, `models.py` | tabele: `users`, `crew`, `measurements`, `checkins`, `keystroke_sessions`, `pvt_results`, `exercise_sessions`, `alerts`, `plan_steps`, `packets`, `access_log`, `rejections`, `revoked_tokens` | tabelele se creează la pornire |
| Seed | `app/db/seed.py` | încarcă `seed/users.json` (parolele trec prin hash-ul echipei de securitate) și scenariul | după pornire, cele 5 conturi există |
| Pragurile | `app/datafiles.py` (**există**) | încarcă `data/parameters.json`, îl validează cu Pydantic și expune pragurile din `praguri_cheie_triaj` ca valori numerice | o valoare lipsă oprește pornirea, cu mesaj clar |
| Catalogul, textele, mediile, scenariul | `app/datafiles.py` (**există**) | `load_all()` încarcă și validează tot `data/`; mock-ul îl folosește deja | rămâne doar să-l apelați din `lifespan` |

Atenție la `parameters.json`: câmpul `valoare` are tipuri diferite (număr, text, listă, dicționar, `null`).
Motorul citește **doar** cele 33 de praguri din `praguri_cheie_triaj`. Unde valoarea e text sau `null`
(`keystroke_baseline_duration`, `shadow_temp_alert_derived`), pragul se scrie în cod, cu un comentariu care spune
că e ales de echipă.

## 2. Conturi și autentificare (P0)

- **Ce face:** fiecare astronaut are contul lui; tokenul leagă fiecare cerere de un singur `crew_id`.
- **Endpoint-uri:** `GET /auth/accounts`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`.
- **Tu scrii:** routerul, tabelul `users`, citirea din seed, regula `crew_access` din `deps.py`.
- **Securitatea scrie:** hash-ul parolei, emiterea și verificarea tokenului, blocarea după 5 parole greșite.
  Tu doar apelezi funcțiile lor (`passwords.verify`, `tokens.issue`, `tokens.decode`, `lockout.check`).
- **Gata când:** `scripts/smoke.py` trece și pe backend-ul real: fiecare cont își vede doar datele lui, comandantul
  primește `403` la datele unui coleg, ofițerul medical primește `200`.

## 3. Misiune, medii, ceas (P0)

- **Endpoint-uri:** `GET /mission`, `GET /environments`, `PUT /mission/environment`, `PUT /sim/clock`.
- **Reguli:**
  - mediile vin din `data/environments.json` (întârziere, gravitație, doză de fond);
  - schimbarea mediului schimbă întârzierea legăturii pentru pachetele **noi**; cele deja pe drum își păstrează ora de sosire;
  - `one_way_delay_real_s = one_way_delay_s / time_scale`.
- **Evenimente:** `environment.changed`.
- **Gata când:** după comutarea pe „Stația spațială”, un pachet nou ajunge în aproximativ o secundă.

## 4. Simulatorul misiunii (P0)

Fără el nu există date. `app/simulator/scenario.py`.

- **Ce face:** generează, la pornire, 140 de zile de măsurători pentru fiecare dintre cei 4 membri: puls de
  noapte, somn, temperatură, tensiune, puls de repaus, HRV, sesiuni de exerciții, check-in-uri.
- **Reguli:**
  - fiecare membru are alt normal personal (de exemplu puls de noapte 54, 58, 61, 52), cu variație zilnică mică;
  - totul e reproductibil: `random.Random(seed)`, cu același seed la fiecare pornire;
  - fiecare valoare e marcată `source = simulated`;
  - evenimentele sunt descrise în `data/scenario/scenario.json`, nu în cod.
- **Evenimentele din scenariu** (aceleași ca în mock):

| Zile | Cine | Ce se întâmplă | Ce demonstrează |
|---|---|---|---|
| 40–41 | toți | somn prost și tastare mai lentă la tot echipajul | **cauză de mediu** (cabina), nu individuală |
| 61–62 | cm-2 | exerciții sărite | recomandarea de împărțire a antrenamentului |
| 93–100 | cm-2 | puls de noapte +3, apoi +7 bpm; temperatură +0,4 °C; somn −1,1 h | boala prinsă înainte de simptome |
| 95–97 | cm-2 | tastare −18%, deși la check-in spune „4/5” | **decalajul de percepție** |
| 97 | toți | furtuna solară (evenimentul DONKI) | radiații, adăpost |
| 110–118 | cm-2 | scorul de pregătire pentru revenire scade, apoi revine | pilonul Inima |

- **Gata când:** `GET /crew/cm-2/timeline` arată aceleași zile colorate la fiecare pornire.

## 5. Baseline-ul personal (P0)

`app/engine/baseline.py`. **Fiecare om e comparat cu el însuși**, nu cu valori clinice generale.

- **Ce face:** pentru fiecare membru și fiecare metrică, calculează normalul personal din zbor: mediana și
  variația (deviația standard sau intervalul 10–90%) pe o fereastră mobilă.
- **Reguli:**
  - baseline-ul se calculează din datele **din zbor**, nu de dinainte: în zbor tensiunea scade normal și pulsul de
    repaus nu crește, deci altfel adaptarea normală ar apărea ca alarmă;
  - minimum 7 nopți pentru pulsul de noapte (`nightsignal_min_nights_baseline`); până atunci `status = unknown`;
  - zilele aflate în alertă nu intră în baseline (altfel boala „devine” normalul).
- **Gata când:** `baseline`, `band_low` și `band_high` din serii sunt diferite pentru fiecare membru.

## 6. Pilonul 1 — Tastatura (P0)

`app/engine/pillars/behavioral.py`, `routers/behavioral.py`.

**Tastarea**

- **Endpoint-uri:** `POST /crew/{id}/keystrokes/batches`, `GET /crew/{id}/keystrokes/summary`.
- **Ce face:** din timpii primiți calculează trăsăturile sesiunii:
  - `hold` = apăsare → eliberare (medie și deviație);
  - `flight` = apăsare → apăsarea următoare (medie și deviație);
  - `backspace_rate` = Backspace-uri / total taste;
  - `keys_per_min`.
- **Reguli:**
  - **nu se salvează niciodată caracterul**; modelul respinge deja orice câmp în plus;
  - loturile cu același `session_id` se adună într-o singură sesiune;
  - baseline-ul = primele N sesiuni ale contului (în demo: cele de la ora 2); până atunci `baseline_ready = false`;
  - `deviation_z` = abaterea fiecărei trăsături, în deviații standard personale;
  - `fatigue_index` (0–100) din `hold` și viteză, cele mai sensibile trăsături; rata de Backspace cântărește puțin;
  - pauzele mai lungi de 2 secunde nu intră în `flight` (sunt pauze de gândire).
- **Gata când:** două sesiuni reale, una odihnit și una obosit, dau indici vizibil diferiți.

**Testul de reacție (PVT-B)**

- **Endpoint-uri:** `POST /crew/{id}/pvt`, `GET /crew/{id}/pvt`.
- **Reguli:** media `1/RT`; lapsus = RT ≥ 355 ms (`pvtb_lapse_threshold`); primele 2–3 teste sunt antrenament și
  nu intră în baseline (`pvt_practice_runs`); `watch` la o abatere de −1,24 SD (`pvt_reliable_change_derived`,
  prag derivat).
- **Gata când:** un test cu reacții lente intenționat trece în `watch`.

## 7. Pilonul 2 — Inima (P1)

`app/engine/pillars/cardio.py`.

- **Ce face:** un scor de „pregătire pentru revenire” (0–100) din pulsul de repaus, HRV și tensiune, toate față de
  baseline-ul din zbor.
- **Reguli (toate derivate, din medicina sportivă; se afișează ca ipoteză):**
  - puls de repaus: media pe 7 zile peste baseline + 1 × variația personală, cel puțin 3 zile → `watch`;
  - HRV (lnRMSSD): media pe 7 zile sub baseline − 0,5 × variația personală → `watch`;
  - cele două împreună, sau însoțite de simptome la check-in → alertă de nivel 2.
- **Onest:** `data_is_simulated = true`, iar `limits_text` spune că pragurile nu sunt publicate pentru astronauți.
- **Gata când:** în zilele 110–118 scorul lui cm-2 scade și apoi revine.

## 8. Pilonul 3 — Santinela (P0)

`app/engine/pillars/immune.py`. Pilonul cu cea mai bună bază științifică; e alerta principală din demo.

- **Regula NightSignal** (Alavi et al. 2022), pe pulsul mediu de noapte față de mediana personală:

| Condiție | Rezultat | Prag din `parameters.json` |
|---|---|---|
| +3 bpm, sau o singură noapte cu ≥ +4 bpm | `watch`, alertă de nivel 1 | `nightsignal_yellow_delta` |
| ≥ +4 bpm, două nopți la rând | `alert`, alertă de nivel 2 | `nightsignal_red_delta_bpm`, `nightsignal_red_consecutive_nights` |
| alertă roșie repetată, cu temperatură crescută sau simptome | propunere de nivel 3 | — |

- **Temperatura:** abatere față de normalul personal din zbor (prag derivat).
- **Indicele de stres** (0–100): indicele de oboseală din tastare + zilele de izolare + doza de radiații. Leagă
  pilonii între ei.
- **Gata când:** alerta lui cm-2 apare în ziua 95 (a doua noapte la +4 bpm), nu mai devreme și nu mai târziu.

## 9. Pilonul 4 — Încărcarea (P1)

`app/engine/pillars/musculoskeletal.py`, `routers/exercise.py`.

- **Endpoint-uri:** `GET /crew/{id}/exercise/today`, `POST /crew/{id}/exercise/sessions`, `GET …/sessions`.
- **Ce face:**
  - scorul sesiunii din repetări × greutate, cu randament descrescător după primele repetări;
  - scorul zilnic = suma sesiunilor; două sesiuni la câteva ore distanță primesc un bonus față de una lungă;
  - `split_recommended = true` când azi e o singură sesiune planificată sau făcută;
  - seria de zile cu antrenamentul împărțit;
  - proiecția de pierdere osoasă: −0,64% pe lună (șold total, cu ARED) în planul actual față de o estimare mai
    bună cu antrenamentul împărțit.
- **Onest:** bonusul pentru sesiuni împărțite vine din studii pe șobolani. `limits_text` și `projection.note`
  spun asta. Densitatea osoasă e estimată, nu măsurată.
- **Praguri:** forță −10% la două teste → nivel 2; −20% → nivel 3 (derivate).
- **Gata când:** după a doua sesiune a zilei, scorul și seria cresc.

## 10. Check-in și decalajul de percepție (P0)

`routers/checkin.py`, `app/engine/perception_gap.py`.

**Check-in**

- **Endpoint-uri:** `GET /checkin/schema`, `POST /crew/{id}/checkins`, `GET …/checkins`, `GET …/checkins/today`.
- **Reguli:**
  - textele și limitele vin din `data/texts/checkin_indicators.json`;
  - o valoare imposibilă **nu** dă eroare: câmpul se salvează `null` și apare în `rejected`;
  - un singur check-in pe zi de misiune; al doilea îl înlocuiește pe primul;
  - valorile sunt marcate `source = manual`;
  - aceeași valoare exactă mai multe zile la rând → `rejected` cu motivul `frozen_sensor` (copiat de ieri).

**Decalajul de percepție — ideea centrală a proiectului**

- `self_score` = starea de spirit × 20.
- `objective_score` = media ponderată a scorurilor obiective: tastare, test de reacție, puls de noapte, somn.
- `gap = self_score − objective_score`. Pozitiv = se simte mai bine decât arată datele.
- `watch` de la 15 puncte, `alert` de la 25 (praguri alese de echipă; se afișează ca atare).
- `explanation` e o propoziție completă, în română, cu cifrele care au contat.
- **Gata când:** un check-in cu „4/5” în ziua 96 întoarce `gap ≈ 28` și `status = alert`.

## 11. Triajul și alertele (P0)

`app/engine/triage.py`, `cross_signals.py`, `routers/alerts.py`.

- **Endpoint-uri:** `GET /crew/{id}/alerts`, `GET /cmo/queue`, `GET /alerts/{id}`, `POST …/ack`,
  `PUT …/plan/steps/{step_id}`, `POST …/escalate`, `POST …/resolve`, `GET /catalog/recommendations`.
- **Ce face motorul:** rulează după fiecare măsurătoare nouă, check-in, sesiune de tastare sau test:
  1. aplică regulile fiecărui pilon;
  2. alege nivelul (1, 2 sau 3) și recomandarea din catalog după `topic` și `level`;
  3. construiește planul de pași din recomandare;
  4. pune `recheck_at` la 1–3 zile;
  5. nu creează a doua alertă pe același subiect cât timp prima e deschisă: o actualizează.
- **Cauză individuală sau de mediu:** dacă cel puțin 3 din 4 membri au aceeași abatere în aceeași zi →
  `cause = environmental`, cu explicația „problema e probabil în cabină”. Altfel `individual`.
- **Semnale încrucișate:** trei abateri mici din piloni diferiți, în aceeași fereastră de 3 zile → un
  `CrossSignal`, cu încredere mai mare decât fiecare în parte.
- **Reverificarea:** la `recheck_at`, dacă valorile au revenit → alerta se închide singură; dacă nu → urcă un nivel.
- **Stări și drepturi:** exact ca în `contract/README.md`, secțiunea 4 (astronautul nu poate trimite la nivelul
  3; nivelul nu coboară; `409` la o stare nepotrivită).
- **Nivelul 3:** creează singur pachetul spre Pământ (secțiunea 13) și completează `packet_id`.
- **Evenimente:** `alert.created`, `alert.updated`, `dashboard.changed`.
- **Gata când:** firul complet din `contract/README.md`, secțiunea 7.6, merge fără mock.

## 12. Tabloul de bord, panourile, derulatorul (P0)

`routers/crew.py`.

- **Endpoint-uri:** `GET /crew`, `GET /crew/{id}/dashboard`, `GET …/pillars/{pillar}`, `GET …/pillars/{pillar}/series`,
  `GET …/timeline`.
- **Ce face:** adună rezultatele motorului în răspunsurile mari pentru interfață; nu calculează nimic nou.
- **Reguli:**
  - `as_of_day=N` întoarce starea de la sfârșitul zilei N (pentru derulator); fără el, starea de acum;
  - `function_text` și `hazard_text` vin din `data/texts/body_functions.json`;
  - sursele fiecărui pilon vin din `parameters.json`;
  - `GET /crew` (doar ofițerul medical) nu conține valori medicale, doar starea generală.
- **Gata când:** autentificat cu conturi diferite vezi date diferite, iar `as_of_day=96` arată alerta lui cm-2.

## 13. Coada navă ↔ Pământ (P0)

`app/link/queue.py`, `scheduler.py`, `windows.py`, `routers/link.py`.

- **Endpoint-uri:** `GET /link/status`, `GET /link/packets`, `GET /link/packets/{id}`, `POST /link/outbox`,
  `POST /earth/replies`, `GET /crew/{id}/messages`.
- **Ce face:** un mesaj nu ajunge direct. Trece prin stările `queued` → `in_transit` → `delivered` sau `rejected`.
- **Planificatorul** (un task `asyncio`, la o secundă reală):
  1. dacă fereastra e deschisă, pachetele `queued` pleacă: `sent_at = now`, `arrives_at = now + întârzierea mediului`;
  2. pachetele cu `arrives_at ≤ now` se deschid cu `security.sealing.open()`;
  3. reușit → `delivered`, iar conținutul devine vizibil; eșuat → `rejected`, cu motivul;
  4. la sosirea unui `earth_reply`: apare în `/crew/{id}/messages` și în `earth_reply` al alertei.
- **Reguli:**
  - conținutul se sigilează la creare cu `security.sealing.seal()`; în tabel stă doar forma criptată;
  - `seq` crește pe fiecare direcție;
  - `progress = (now − sent_at) / (arrives_at − sent_at)`, între 0 și 1; `eta_real_s` în secunde reale;
  - `payload` se întoarce doar pentru pachetele `delivered` și doar rolului care are voie să-l citească.
- **Evenimente:** `packet.sent`, `packet.arrived`, `packet.rejected`.
- **Gata când:** un răspuns scris în Controlul misiunii apare la astronaut după două întârzieri complete.

## 14. Radiații și furtuna solară (P1)

`app/simulator/radiation.py`, `app/engine/radiation.py`, `routers/radiation.py`.

- **Endpoint-uri:** `GET /radiation/status`, `GET /radiation/series`, `GET /radiation/events`,
  `POST /radiation/shelter-ack`, `POST /sim/sep/start`, `POST /sim/sep/stop`.
- **Generatorul:** doza de fond a mediului + zgomot mic; la furtună, o curbă care urcă repede și scade lent.
  Forma e sintetică (`profile_is_synthetic = true`); orele vin din `data/donki/donki_sep_event.json`.
- **Detectorul:** media mobilă pe 24 h; alertă când rata e ≥ 2 × medie la 3 citiri la rând
  (`prag_alerta_sep_rata_vs_baseline`, derivat).
- **După alertă:**
  1. alertă de nivel 1 cu recomandarea „mergi în adăpost”;
  2. `shelter-ack` aplică factorul de ecranare și salvează ora;
  3. avertizarea Pământului pleacă prin coadă ca pachet `donki_alert`, direcția `up`;
  4. la sosirea ei se calculează `lead_minutes`;
  5. dacă doza din eveniment trece de 25 mGy-Eq (`prag_doza_eveniment_nivel3`) → pachet de nivel 3.
- **Evenimente:** `radiation.alert`, `radiation.reading` (cel mult unul la 2 secunde reale), `radiation.cleared`.
- **Gata când:** de la „Pornește furtuna” până la „adăpost activ cu N minute înainte de avertizarea Pământului”
  totul merge fără nicio apăsare în plus, în afară de „Sunt în adăpost”.

## 15. Evenimente live (P0)

`routers/events.py`, `publish()` din `deps.py` (există deja).

- De adăugat: `mission.tick` din `SimClock`, la o secundă reală; comentariul `: ping` la 15 secunde; filtrarea pe
  cont există deja.
- **Regulă:** orice schimbare de stare apelează `publish()`. Lista evenimentelor: `contract/README.md`, secțiunea 6.
- **Gata când:** două ferestre de browser, cu două conturi, primesc fiecare doar evenimentele lui.

## 16. Medicul AI: puntea (P1)

`routers/ai.py`. Un singur fișier; modelul e treaba echipei de AI.

- **Endpoint-uri:** `GET /ai/status`, `POST /ai/chat`.
- **Ce faci tu:**
  1. verifici că astronautul întreabă despre el însuși;
  2. construiești contextul: alerta, dovezile, recomandarea din catalog;
  3. apelezi `POST {AI_URL}/chat`, cu limită de 20 de secunde;
  4. dacă nu răspunde: întorci textul recomandării din catalog, cu `fallback = true`. **Niciodată eroare.**
- **Gata când:** cu serviciul AI oprit, cardul afișează în continuare recomandarea din catalog.

## 17. Dovezi, jurnal, demo (P1)

- `GET /evidence/tests`: rulează pytest la pornire (sau citește ultimul raport) și întoarce rezultatele.
- `GET /evidence/parameters`: pragurile din `parameters.json`, cu sursă și cu marcajele verificat/derivat.
- `GET /access-log`, `GET /security/rejections`: citesc tabelele; scrierea o face codul echipei de securitate.
- `POST /ingest/measurements`: primește o măsurătoare, apelează `security.signing.verify()` și
  `security.validation.check()`, apoi o salvează sau o respinge.
- `POST /demo/inject-spoof`, `POST /demo/frozen-sensor`: pornesc scripturile de atac din interior.
- `POST /sim/reset`: reîncarcă scenariul și golește tot ce s-a schimbat în demo. **Se folosește între repetiții.**
- **Teste pytest** (`tests/`), cel puțin: regula NightSignal, detectorul de furtună, decalajul de percepție,
  cauza de mediu, pachetul respins, conturile separate.

---

## 18. Împărțirea între cei doi

| | Backend A | Backend B |
|---|---|---|
| Orele 0–2 | uv, `config`, `clock`, baza de date, seed | încărcarea `parameters.json` și a catalogului; scheletul simulatorului |
| Orele 2–10 | conturi (§2), misiune (§3), check-in și decalaj (§10), tabloul de bord (§12), evenimente (§15) | simulator (§4), baseline (§5), Tastatura (§6), Santinela (§8), triaj (§11) |
| Ora 10 | **prima integrare cap-coadă, împreună cu frontend-ul** | |
| Orele 10–16 | coada (§13), puntea AI (§16) | Inima (§7), Încărcarea (§9), radiații (§14) |
| Orele 16–18 | dovezi, jurnal, demo, reset (§17) | teste pytest, reglarea scenariului |
| Orele 18–24 | bug-uri, repetiții | bug-uri, repetiții |

Dacă rămâneți în urmă, tăiați în ordinea: Inima (§7) → proiecția osoasă din §9 → reverificarea automată din §11
→ pachetul DONKI din §14. Nu tăiați: Santinela, decalajul de percepție, coada cu întârziere.

## 19. Cu cine te legi

| Cu cine | Ce | Unde | Când se stabilește |
|---|---|---|---|
| **Frontend** | contractul API: toate endpoint-urile și evenimentele | `contract/`, `app/schemas.py` | există; orice schimbare se anunță |
| **Securitate** | funcțiile pe care le apelezi: `passwords.hash/verify`, `tokens.issue/decode`, `lockout.check`, `sealing.seal/open`, `signing.verify`, `validation.check`, `access_log.write` | `backend/app/security/` | ora 0–1: semnăturile funcțiilor; ei pot începe cu variante simple |
| **AI** | un singur apel: `POST {AI_URL}/chat` și `GET {AI_URL}/status` | `routers/ai.py` ↔ `ai/service/` | ora 0–1: forma cererii și a răspunsului |
| **Data** | fișierele pe care le citești | `data/` | ora 0–2: formatul fiecărui fișier (`DATA_SARCINI.md`) |

Regula comună cu securitatea: în primele ore, funcțiile lor pot fi variante simple (hash real, dar `seal` care
doar semnează). Tu le apelezi de la început prin aceleași nume, iar ei le întăresc fără să-ți atingă codul.

## 20. Scheletul gol

```
backend/
├── README.md
├── pyproject.toml
├── uv.lock
├── .python-version
├── Dockerfile
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── schemas.py
│   ├── ai_schemas.py
│   ├── datafiles.py
│   ├── deps.py
│   ├── examples.py
│   ├── config.py
│   ├── clock.py
│   ├── routers/
│   │   ├── auth.py        mission.py     crew.py        checkin.py
│   │   ├── behavioral.py  exercise.py    alerts.py      link.py
│   │   └── radiation.py   ai.py          security.py    demo.py     events.py
│   ├── db/
│   │   ├── session.py
│   │   ├── models.py
│   │   └── seed.py
│   ├── engine/
│   │   ├── baseline.py
│   │   ├── triage.py
│   │   ├── perception_gap.py
│   │   ├── cross_signals.py
│   │   ├── radiation.py
│   │   └── pillars/
│   │       ├── behavioral.py
│   │       ├── cardio.py
│   │       ├── immune.py
│   │       └── musculoskeletal.py
│   ├── simulator/
│   │   ├── scenario.py
│   │   ├── radiation.py
│   │   └── devices.py
│   ├── link/
│   │   ├── queue.py
│   │   ├── scheduler.py
│   │   └── windows.py
│   └── security/            ← al echipei de securitate; tu doar îl apelezi
├── tests/
│   ├── conftest.py
│   ├── routers/
│   ├── engine/
│   ├── link/
│   └── security/
└── seed/
    └── users.json
```
