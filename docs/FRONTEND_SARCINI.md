# Frontend — ce trebuie implementat

**Folder:** `frontend/` · **Echipa:** 2 oameni · **Unelte:** Next.js (App Router), TypeScript, Tailwind

Frontend-ul este tot ce vede juriul. Afișează ce calculează backend-ul și trimite înapoi ce face utilizatorul.
**Nu calculează statusuri, praguri sau alerte**: backend-ul trimite `status`, frontend-ul îl colorează.

**De unde pornești:** `src/lib/api.ts` (client tipizat, login, evenimente live, colectorul de tastare) și
`src/lib/shadow-api.d.ts` (tipurile, contract 1.2) există deja; după o schimbare de contract le regenerezi cu
`bash scripts/gen_types.sh`. Serverul mock răspunde la toate endpoint-urile, deci poți
construi fiecare ecran fără să aștepți backend-ul. Referința: `contract/README.md`. Aspectul: mockup-ul
„SHADOW — interfața” și `docs/design/`.

**Priorități:** `P0` = fără el nu merge demo-ul · `P1` = intră în demo dacă e gata până la ora 16 · `P2` = bonus.

## Cuprins

1. [Fundația](#1-fundația-p0-orele-02)
2. [Autentificarea: „Cine ești?”](#2-autentificarea-cine-ești-p0)
3. [Cadrul aplicației](#3-cadrul-aplicației-p0)
4. [Ecranul astronautului: corpul interactiv](#4-ecranul-astronautului-corpul-interactiv-p0)
5. [Panoul unei zone](#5-panoul-unei-zone-p0)
6. [Decalajul de percepție](#6-decalajul-de-percepție-p0)
7. [Check-in-ul de dimineață](#7-check-in-ul-de-dimineață-p0)
8. [Tastarea](#8-tastarea-p0)
9. [Testul de reacție](#9-testul-de-reacție-p1)
10. [Alerta și planul de acțiune](#10-alerta-și-planul-de-acțiune-p0)
11. [Medicul AI](#11-medicul-ai-p1)
12. [Exercițiile](#12-exercițiile-p1)
13. [Coada ofițerului medical](#13-coada-ofițerului-medical-p0)
14. [Controlul misiunii](#14-controlul-misiunii-p0)
15. [Furtuna solară](#15-furtuna-solară-p1)
16. [Evidence](#16-evidence-p1)
17. [Derulatorul și comutatorul de mediu](#17-derulatorul-și-comutatorul-de-mediu-p1)
18. [Reguli de interfață](#18-reguli-de-interfață)
19. [Împărțirea între cei doi](#19-împărțirea-între-cei-doi)
20. [Cu cine te legi](#20-cu-cine-te-legi)
21. [Scheletul gol](#21-scheletul-gol)

---

## 1. Fundația (P0, orele 0–2)

| Ce | Unde | Gata când |
|---|---|---|
| Proiectul Next.js + Tailwind | `frontend/` (**gata**) | `npm run dev` pornește pe portul 3000 |
| Clientul API | `src/lib/api.ts`, `shadow-api.d.ts` (copiate din zip) | un apel către mock întoarce date tipizate |
| Tema | `src/styles/tokens.css` (**gata**, din Quaternion) | culorile, fonturile și spațierile sunt variabile CSS |
| Fonturile locale | `public/fonts/` | Geist și Geist Mono se încarcă fără internet |
| Etichetele de stare | `StatusBadge` din `components/ui` (**gata**) | fiecare stare are culoare **și** formă **și** cuvânt |
| Rutele goale | `src/app/` | fiecare ecran din scheletul de mai jos există, chiar dacă e gol |

**Sistemul de design e gata (v2, „Semnal pe negru”):** `frontend/DESIGN.md`, catalogul vizual la `/kit`.
Paleta vine din logo (negru `#0b0a0f`, crem `#fef7ea`); singurele culori sunt cele de stare: `ok` `#75dbb6` ●,
`watch` `#f5c25f` ▲, `alert` `#fa6863` ■, `unknown` neutru ○ (mereu prin `<StatusBadge />`). Pilonii nu au culoare.
**Interfața e în engleză**; textele de conținut vin de la backend și se afișează cum vin.

## 2. Autentificarea: „Cine ești?” (P0)

`src/app/login/`, `src/lib/auth.tsx`.

- **Ce face:** fiecare astronaut are contul lui. Ecranul arată câte o casetă pe cont (nume, inițiale); la click
  cere parola acelui cont.
- **Endpoint-uri:** `GET /auth/accounts`, `POST /auth/login`, `POST /auth/logout`.
- **Reguli:**
  - la bord apar conturile cu `location = "ship"`; contul `earth` apare pe `/mission-control`;
  - tokenul stă în memorie (stare React), nu în `localStorage`;
  - după login, `user.role` decide ecranul: `astronaut` → `/dashboard`, `cmo` → `/cmo`, `earth` → `/mission-control`;
  - la `401` oriunde în aplicație → înapoi la `/login`;
  - la `429`: mesajul primit + numărătoare inversă din `details.retry_after_s`.
- **Schimbarea astronautului** (butonul din antet), în această ordine:
  1. oprește colectorul de tastare;
  2. închide conexiunea de evenimente;
  3. `logout()`;
  4. golește **toate** datele încărcate;
  5. arată „Cine ești?”.
- **Gata când:** te autentifici ca `specialist2`, apoi ca `comandant`, și pe ecran nu rămâne nimic de la primul.

## 3. Cadrul aplicației (P0)

`src/app/(ship)/layout.tsx`, `src/lib/events.tsx`, `components/layout/`.

- **Antetul:** numele și inițialele contului autentificat (mereu vizibile), ziua și ora misiunii, mediul curent,
  starea legăturii cu Pământul (întârzierea), butonul de schimbare a astronautului.
- **Evenimentele live:** un singur abonament la `/events`, deschis după login. Celelalte componente ascultă prin
  context, nu deschid conexiuni proprii.
- **Ce face la fiecare eveniment:** tabelul din `contract/README.md`, secțiunea 6. Pe scurt:

| Eveniment | Reacție |
|---|---|
| `mission.tick` | actualizează ceasul |
| `dashboard.changed`, `alert.created`, `alert.updated` | reîncarcă tabloul de bord și panoul deschis |
| `packet.*` | actualizează coada și mesajele |
| `radiation.alert` / `radiation.cleared` | arată / ascunde banner-ul de adăpost |
| reconectare | reîncarcă datele ecranului curent |

- **Fără polling.** Niciun `setInterval` care cere date.
- **Gata când:** o alertă creată din Swagger apare pe ecran fără reîncărcarea paginii.

## 4. Ecranul astronautului: corpul interactiv (P0)

`src/app/(ship)/dashboard/`, `components/body/`.

- **Endpoint:** `GET /crew/{crew_id}/dashboard`. Un singur apel aduce tot.
- **Ce afișează:**
  - ilustrația corpului (o imagine existentă, cu licență liberă), cu **patru zone** apăsabile: creier, inimă,
    sistem imunitar, oase și mușchi;
  - fiecare zonă colorată după `status`, cu numele pilonului și `headline`;
  - cardul decalajului de percepție (secțiunea 6);
  - banner-ul alertei principale (`top_alert`);
  - semnalele încrucișate;
  - seriile de zile și reamintirile zilei.
- **Reguli:**
  - zonele sunt butoane reale (`<button>`), invizibile, peste ilustrație; se pot folosi și de la tastatură;
  - sursa și licența ilustrației apar în pagina proiectului;
  - tranziție la schimbarea culorii unei zone.
- **Gata când:** cu contul `specialist2` zona imunitară e roșie, iar cu `comandant` toate sunt verzi.

## 5. Panoul unei zone (P0)

`components/body/ZonePanel`.

- **Endpoint:** `GET /crew/{crew_id}/pillars/{pillar}`.
- **Ce afișează, în această ordine** (ordinea e cerută de brief):
  1. funcția părții corpului (`function_text`);
  2. pericolul spațial (`hazard_text`);
  3. valorile, fiecare cu normalul personal și abaterea (`metrics`);
  4. graficul, cu banda normală și pragul de alertă (`chart`);
  5. explicația (`explanation`);
  6. planul de acțiune cu bife (`plan_steps`) și data reverificării;
  7. sursele, cu link (`sources`) și marcajul „ipoteză” unde sursa e neverificată sau derivată;
  8. limitele oneste (`limits_text`).
- **Reguli:** eticheta „date simulate” când `data_is_simulated = true`; bifa unui pas apelează
  `PUT /alerts/{alert_id}/plan/steps/{step_id}`.
- **Gata când:** click pe fiecare dintre cele patru zone deschide panoul corect.

## 6. Decalajul de percepție (P0)

Componenta care spune povestea proiectului. `components/body/PerceptionGap`.

- **Date:** `dashboard.perception_gap`.
- **Ce afișează:** două bare alăturate, „Cum spui că te simți” (`self_score`) și „Ce arată datele”
  (`objective_score`); diferența dintre ele, evidențiată; propoziția `explanation`; lista `contributing_signals`.
- **Gata când:** un jurat înțelege ideea în cinci secunde, fără să citească altceva.

## 7. Check-in-ul de dimineață (P0)

`src/app/(ship)/checkin/`, `components/checkin/`.

- **Endpoint-uri:** `GET /crew/{id}/checkins/today`, `GET /checkin/schema`, `POST /crew/{id}/checkins`.
- **Ce face:**
  - formularul se construiește **din schemă**, nu din cod: câmpurile, unitățile, limitele și cele trei texte
    („Cum se măsoară”, „Ce înseamnă valoarea”, „De ce contează în spațiu”);
  - starea de spirit pe scara 1–5; valorile numerice; întrebarea despre mese;
  - nota liberă trimite ritmul tastării cu `context = "checkin_note"`.
- **După trimitere:**
  - câmpurile din `rejected` primesc mesajul lor lângă ele („măsoară din nou”); restul rămân salvate;
  - apare imediat decalajul de percepție recalculat;
  - apare seria de zile.
- **Gata când:** o temperatură de 41,9 °C dă mesaj lângă câmp, iar restul check-in-ului se salvează.

## 8. Tastarea (P0)

`components/keystrokes/`, `createKeystrokeCollector` din `api.ts`.

- **Endpoint-uri:** `POST /crew/{id}/keystrokes/batches`, `GET /crew/{id}/keystrokes/summary`.
- **Ce face:**
  - un câmp de text liber în care utilizatorul scrie; colectorul trimite **doar timpii și clasa tastei**;
  - barele live: câte o bară pe apăsare, cu înălțimea după durata apăsării, fără litere;
  - cardul „Ritmul tău”: viteza, timpul de apăsare, indicele de oboseală, față de normalul personal;
  - comparația din demo: sesiunea de la ora 2 lângă cea de la ora 18–20.
- **Reguli:**
  - un text vizibil lângă câmp: „SHADOW nu citește ce scrii, doar ritmul”;
  - **nu trimiteți niciodată `event.key`**; backend-ul respinge oricum câmpurile în plus;
  - colectorul se oprește la schimbarea astronautului.
- **Gata când:** un jurat tastează o propoziție și își vede ritmul pe ecran, fără text.

## 9. Testul de reacție (P1)

`src/app/(ship)/pvt/`.

- **Endpoint:** `POST /crew/{id}/pvt`.
- **Ce face:** testul de 3 minute rulează integral în browser. Un stimul apare la intervale aleatoare de 1–4
  secunde; utilizatorul apasă cât de repede poate; se măsoară timpul cu `performance.now()`.
- **Reguli:** apăsarea înainte de stimul e `false_start`; lipsa răspunsului în 3 secunde e `rt_ms = null`; la
  sfârșit se trimit toate încercările într-un singur apel. Pentru demo, un buton „variantă scurtă, 30 de secunde”.
- **Gata când:** rezultatul apare cu viteza medie, lapsusurile și abaterea față de normal.

## 10. Alerta și planul de acțiune (P0)

`src/app/(ship)/alerts/[id]/`, `components/alerts/`.

- **Endpoint-uri:** `GET /alerts/{id}`, `POST …/ack`, `PUT …/plan/steps/{step_id}`, `POST …/escalate`, `POST …/resolve`.
- **Ce afișează:** titlul și nivelul; ce s-a observat; dovezile, cu abaterea fiecăreia; cauza (individuală sau de
  mediu); recomandarea din catalog, cu sursă; planul cu bife; data reverificării; istoricul; răspunsul Pământului,
  dacă a sosit.
- **Butoanele, după rol:**

| Buton | Cine îl vede | Apel |
|---|---|---|
| „Am văzut” | astronautul | `ack` |
| „Anunță ofițerul medical” | astronautul | `escalate` cu `to_level: 2` |
| „Trimite pe Pământ” | doar ofițerul medical | `escalate` cu `to_level: 3` |
| „Închide” | astronautul la nivelul 1; ofițerul medical la 2 și 3 | `resolve` |

- **Gata când:** firul din `contract/README.md`, secțiunea 7.6, se poate parcurge doar din interfață.

## 11. Medicul AI (P1)

`components/ai/`.

- **Endpoint-uri:** `GET /ai/status`, `POST /ai/chat`.
- **Ce afișează:** un card cu întrebarea, răspunsul, **sursele citate** (titlu, link, fragment) și mențiunea
  „Prototip de sprijin, nu dispozitiv medical”.
- **Reguli:**
  - stare de încărcare vizibilă (răspunsul poate dura 5–15 secunde);
  - dacă `fallback = true`: eticheta „Text din catalog (modelul nu a răspuns)”;
  - dacă `citations` e gol: „fără sursă”;
  - afișați unde rulează modelul (`mode`): `local`, `colab_simulation` (simulare), `fallback` (doar catalogul) sau
    `mock` (serviciul AI încă fără model).
- **Gata când:** cu Wi-Fi-ul oprit, cardul răspunde și arată sursele.

## 12. Exercițiile (P1)

`components/body/` (în panoul „Încărcarea”) sau un card separat.

- **Endpoint-uri:** `GET /crew/{id}/exercise/today`, `POST /crew/{id}/exercise/sessions`.
- **Ce afișează:** sesiunile planificate și făcute; scorul de încărcare față de țintă; recomandarea de împărțire;
  seria de zile; proiecția osoasă, cu nota că e estimare.
- **Gata când:** după înregistrarea celei de-a doua sesiuni, scorul și seria cresc pe ecran.

## 13. Coada ofițerului medical (P0)

`src/app/(ship)/cmo/`.

- **Endpoint-uri:** `GET /cmo/queue`, `GET /crew`, apoi ecranul alertei (secțiunea 10).
- **Ce afișează:** alertele de nivel 2 și 3 din tot echipajul, cele mai grave primele; lista echipajului doar cu
  starea generală. Ofițerul medical are și propriul ecran de astronaut (`/dashboard`), cu datele lui.
- **Gata când:** alerta escaladată de `specialist2` apare aici fără reîncărcare.

## 14. Controlul misiunii (P0)

`src/app/mission-control/`, `components/link/`. Ecranul Pământului; singurul cu portocaliu.

- **Endpoint-uri:** `GET /link/status`, `GET /link/packets`, `GET /link/packets/{id}`, `POST /earth/replies`.
- **Ce afișează:**
  - întârzierea într-un sens, cât mai e fereastra deschisă, factorul de accelerare;
  - **bara de progres a pachetului** între „NAVA” și „PĂMÂNT”;
  - tabelul cozii: mesaj, de la cine, stare (`ÎN DRUM`, `SOSIT`, `RESPINS`), semnătură;
  - conținutul unui pachet sosit;
  - formularul de răspuns, cu textul „răspunsul ajunge după …”.
- **Reguli:**
  - bara se animă local, cu durata `eta_real_s`; lista se reîncarcă doar la `packet.sent`, `packet.arrived`,
    `packet.rejected`;
  - un pachet respins apare roșu, cu „semnătură invalidă”;
  - conținutul apare **abia după sosire**: asta arată întârzierea.
- **Gata când:** juriul vede pachetul călătorind și ajungând.

## 15. Furtuna solară (P1)

`components/radiation/`.

- **Endpoint-uri:** `GET /radiation/status`, `GET /radiation/series`, `POST /radiation/shelter-ack`.
- **Ce afișează:**
  - banner pe tot ecranul la `radiation.alert`: „Mergi în adăpost”, cu butonul „Sunt în adăpost”;
  - curba dozei, cu pragul de alertă și cu eticheta „curbă sintetică, eveniment real NASA DONKI”;
  - după sosirea avertizării de pe Pământ: **„Adăpost activ cu N minute înainte de avertizarea Pământului”**,
    cu cifra mare (`lead_minutes`).
- **Gata când:** de la pornirea furtunii până la cifra finală, totul apare singur pe ecran.

## 16. Evidence (P1)

`src/app/(ship)/evidence/`.

- **Endpoint-uri:** `GET /evidence/tests`, `GET /evidence/parameters`, `GET /access-log`, `GET /security/rejections`.
- **Ce afișează:** testele automate (trecute / picate); pragurile cu sursa fiecăruia și marcajele
  verificat / neverificat, publicat / derivat; jurnalul de acces („cine mi-a citit datele”); valorile și
  pachetele respinse.
- **Gata când:** juriul poate verifica de unde vine orice cifră din aplicație.

## 17. Derulatorul și comutatorul de mediu (P1)

`components/layout/`.

- **Derulatorul:** `GET /crew/{id}/timeline` întoarce doar zilele **care au avut loc** (misiunea pornește în ziua
  96). Bara are `total_days` poziții (din `/mission`): zilele trecute colorate după stare, cu etichete la
  evenimente, iar restul „încă nu”. Se reîncarcă la `mission.tick` când se schimbă ziua. Când utilizatorul se
  oprește pe o zi: `dashboard?as_of_day=N` și panoul deschis cu același parametru (`N` ≤ ziua curentă, altfel 422).
  Derulatorul doar citește; nu schimbă ceasul.
- **Comutatorul de mediu:** `GET /environments`, `PUT /mission/environment`; arată noua întârziere.
- **Panoul de demo** (ascuns, la o combinație de taste): „Pornește furtuna”, „Pachet falsificat”,
  „Senzor înghețat”, „Reset”, schimbarea vitezei ceasului.
- **Gata când:** tragi de bară și zonele corpului își schimbă culoarea zi cu zi.

---

## 18. Reguli de interfață

- **Culoarea nu apare niciodată singură:** mereu cu formă și cuvânt.
- **Textele vin de la backend, în română.** Nu traduceți și nu compuneți mesaje din bucăți.
- **„Date simulate”** apare oriunde `source = simulated` sau `data_is_simulated = true`.
- **Timpul:** se afișează timpul misiunii; animațiile folosesc câmpurile `_real_s`.
- **Erorile:** `ApiError.message` se poate afișa direct. Tabelul complet: `contract/README.md`, secțiunea 5.
- **Offline:** fără fonturi, imagini sau scripturi de pe internet.
- **Accesibilitate:** butoane reale, focus vizibil, contrast suficient pe negru.

## 19. Împărțirea între cei doi

| | Frontend A | Frontend B |
|---|---|---|
| Orele 0–2 | proiect, temă, fonturi, etichete de stare | client API, context de autentificare, context de evenimente, rute goale |
| Orele 2–10 | corpul interactiv (§4), panoul zonei (§5), decalajul (§6), tastarea (§8) | „Cine ești?” (§2), cadrul (§3), check-in (§7), alerta (§10) |
| Ora 10 | **prima integrare cap-coadă, împreună cu backend-ul** | |
| Orele 10–16 | medicul AI (§11), exercițiile (§12), furtuna (§15) | coada ofițerului medical (§13), Controlul misiunii (§14), testul de reacție (§9) |
| Orele 16–18 | derulatorul, animațiile (§17) | Evidence (§16), comutatorul de mediu, panoul de demo |
| Orele 18–24 | bug-uri, video de rezervă, repetiții | bug-uri, repetiții |

Comune (se anunță înainte de schimbări): `src/lib/`, `components/ui/`, `styles/tokens.css`.

Dacă rămâneți în urmă, tăiați în ordinea: testul de reacție complet (rămâne varianta scurtă) → derulatorul →
exercițiile → Evidence redus la praguri și teste.

## 20. Cu cine te legi

| Cu cine | Ce | Unde | Când se stabilește |
|---|---|---|---|
| **Backend** | contractul API: endpoint-uri, modele, evenimente | `contract/README.md`, `src/lib/shadow-api.d.ts` | există; după orice schimbare regenerezi tipurile |
| **Securitate** | regulile de autentificare: token în memorie, schimbarea astronautului, doar clasa tastei | `src/lib/auth.tsx`, colectorul de tastare | ora 0–2 |
| **AI** | nimic direct: vorbești doar cu `/ai/chat` din backend | `components/ai/` | — |
| **Data** | nimic direct: textele vin prin backend (`/checkin/schema`, panoul zonei) | — | — |

Frontend-ul vorbește **doar cu backend-ul**. Nu citește fișiere din `data/` și nu apelează serviciul AI.

## 21. Scheletul gol

```
frontend/
├── README.md
├── package.json
├── tsconfig.json
├── next.config.ts
├── .env.local.example
├── Dockerfile
├── public/
│   ├── body/
│   └── fonts/
└── src/
    ├── app/
    │   ├── layout.tsx
    │   ├── globals.css
    │   ├── page.tsx
    │   ├── login/
    │   ├── (ship)/
    │   │   ├── layout.tsx
    │   │   ├── dashboard/
    │   │   ├── checkin/
    │   │   ├── pvt/
    │   │   ├── alerts/[id]/
    │   │   ├── cmo/
    │   │   └── evidence/
    │   └── mission-control/
    ├── components/
    │   ├── body/
    │   ├── charts/
    │   ├── checkin/
    │   ├── keystrokes/
    │   ├── alerts/
    │   ├── link/
    │   ├── radiation/
    │   ├── ai/
    │   ├── layout/
    │   └── ui/
    ├── lib/
    │   ├── api.ts
    │   ├── shadow-api.d.ts
    │   ├── auth.tsx
    │   ├── events.tsx
    │   └── format.ts
    ├── hooks/
    └── styles/
        └── tokens.css
```
