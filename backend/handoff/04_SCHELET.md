# 04 — Scheletul backend-ului

**Generat** de `scripts/build_handoff.py`. Fiecare fișier din `backend/`, ce face și taskul care îl implementează.
„gata” = funcționează deja; „mock” = răspunde cu date de exemplu până la taskul indicat; `Txx` = schelet
(semnături + `NotImplementedError("Txx")`).

| Fișier | Stare | Ce face |
|---|---|---|
| `backend/.python-version` | gata | 3.12 |
| `backend/PLAN_DE_ATAC_BACKEND.md` | gata | planul: arhitectura, regulile, orele |
| `backend/README.md` | gata | cum pornești |
| `backend/app/ai_schemas.py` | gata | SHADOW — contractul dintre backend și serviciul AI (portul 8001). COPIE a ai/service/schemas.py. |
| `backend/app/clock.py` | T02 | SimClock: SINGURA sursă de timp din aplicație. TASK T02. |
| `backend/app/config.py` | gata | Setările, citite din .env / mediu (pydantic-settings). TASK T01. |
| `backend/app/datafiles.py` | gata | SHADOW — contractul dintre backend și folderul data/. |
| `backend/app/db/__init__.py` | gata | Baza de date: SQLite asincron (aiosqlite), recreată la fiecare pornire. Vezi handoff/03_BAZA_DE_DATE.md. |
| `backend/app/db/base.py` | gata | Baza declarativă și tipurile comune. Verificat (plan, secțiunea 5). |
| `backend/app/db/models/__init__.py` | gata | Toate tabelele. Importul acestui pachet le înregistrează pe Base.metadata (necesar înainte de create_all). |
| `backend/app/db/models/alerts.py` | gata | Alertele, pașii planului și istoricul lor. |
| `backend/app/db/models/link.py` | gata | Coada navă ↔ Pământ. |
| `backend/app/db/models/measurements.py` | gata | Datele astronauților: măsurători, check-in-uri, tastare, teste de reacție, exerciții, radiații. |
| `backend/app/db/models/security.py` | gata | Jurnalul de acces (doar INSERT) și respingerile. Scrise de codul echipei de securitate. |
| `backend/app/db/models/sim.py` | gata | Starea simulatorului și contoarele, ca perechi cheie → valoare JSON. |
| `backend/app/db/models/users.py` | gata | Echipajul, conturile și tokenurile revocate. |
| `backend/app/db/repos.py` | T13 | Interogări refolosite (citiri). TASK T13. Toate primesc sesiunea și întorc tipuri din engine/types.py, |
| `backend/app/db/seed.py` | T06, T11 | Seed-ul de la pornire. TASK T06 (echipaj + conturi) și T11 (istoricul). |
| `backend/app/db/session.py` | gata | Motorul asincron și sesiunea. Verificat (plan, secțiunea 5). |
| `backend/app/deps.py` | gata | Autentificare și permisiuni — varianta MOCK. |
| `backend/app/engine/__init__.py` | gata | Motorul: funcții PURE. Primesc date simple, întorc rezultate simple. NU importă db/, fastapi, clock, security. |
| `backend/app/engine/baseline.py` | T12 | Normalul personal din zbor. TASK T12. |
| `backend/app/engine/cross_signals.py` | T29 | Semnale încrucișate și cauza de mediu. TASK T29. |
| `backend/app/engine/derived.py` | gata | Pragurile ALESE DE ECHIPĂ (nu sunt în literatură). Singurul loc din motor cu cifre scrise direct. |
| `backend/app/engine/perception_gap.py` | T18 | Decalajul de percepție — ideea centrală. TASK T18. |
| `backend/app/engine/pillars/__init__.py` | gata | Cei patru piloni. Fiecare: funcții pure care primesc serii + baseline + praguri și întorc Finding / PillarScore. |
| `backend/app/engine/pillars/behavioral.py` | T19, T20 | Tastatura: trăsăturile tastării, indicele de oboseală, PVT-B. TASK T19 (tastare) și T20 (PVT). |
| `backend/app/engine/pillars/cardio.py` | T27 | Inima: scorul de pregătire pentru revenire. Praguri DERIVATE (medicina sportivă). TASK T27. |
| `backend/app/engine/pillars/immune.py` | T14 | Santinela: NightSignal (Alavi et al. 2022), temperatura, indicele de stres. TASK T14. |
| `backend/app/engine/pillars/musculoskeletal.py` | T28 | Încărcarea: stimulul osos, recomandarea de împărțire, proiecția. Efect demonstrat DOAR pe animale. TASK T28. |
| `backend/app/engine/radiation.py` | T25 | Detectorul de furtună. TASK T25. |
| `backend/app/engine/triage.py` | T15 | Triajul: din constatări + alertele deschise → ce se creează, se actualizează sau se escaladează. TASK T15. |
| `backend/app/engine/types.py` | gata | Tipurile motorului (separate de tabele și de contract). Gata, nu e un task. |
| `backend/app/examples.py` | gata | Date de exemplu pentru MOCK. Backend-ul le înlocuiește treptat cu date reale; |
| `backend/app/ids.py` | T04 | Id-urile cu prefix din contract (al-0001, pk-0007, ck-0096 …). TASK T04. |
| `backend/app/link/__init__.py` | gata | Coada navă ↔ Pământ. Sigilarea (semnătură + criptare) vine din security/sealing.py; replay-ul îl blocăm noi. |
| `backend/app/link/queue.py` | T23 | Crearea pachetelor. TASK T23. |
| `backend/app/link/scheduler.py` | T24 | Planificatorul cozii. Task din fundal, pas 1 s real. TASK T24. |
| `backend/app/link/windows.py` | T24 | Ferestrele de comunicare și întârzierea pe mediu. TASK T24. |
| `backend/app/main.py` | gata | SHADOW API — scheletul contractului. |
| `backend/app/routers/ai.py` | mock → T31 |  |
| `backend/app/routers/alerts.py` | mock → T17 |  |
| `backend/app/routers/auth.py` | mock → T07 |  |
| `backend/app/routers/behavioral.py` | mock → T19, T20 |  |
| `backend/app/routers/checkin.py` | mock → T18 |  |
| `backend/app/routers/crew.py` | mock → T21 |  |
| `backend/app/routers/demo.py` | mock → T33 |  |
| `backend/app/routers/events.py` | mock → T22 |  |
| `backend/app/routers/exercise.py` | mock → T28 |  |
| `backend/app/routers/link.py` | mock → T23, T24 |  |
| `backend/app/routers/mission.py` | mock → T09 |  |
| `backend/app/routers/radiation.py` | mock → T25, T26 |  |
| `backend/app/routers/security.py` | mock → T08, T32 |  |
| `backend/app/schemas.py` | gata | SHADOW — contractul de date (Pydantic v2). |
| `backend/app/security/__init__.py` | gata | SHADOW — codul de securitate din aplicație (echipa de securitate). |
| `backend/app/security/access_log.py` | gata | Jurnalul de acces: doar se adaugă; fiecare intrare conține hash-ul celei dinainte. |
| `backend/app/security/errors.py` | gata | Excepțiile pe care le aruncă pachetul de securitate. Backend-ul le prinde și le transformă în erori API. |
| `backend/app/security/keys.py` | gata | Cheile. Se generează cu security/keys/generate_keys.py și NU intră în git. |
| `backend/app/security/lockout.py` | gata | Blocarea contului după prea multe parole greșite. Blocarea e PE CONT: nu-i afectează pe ceilalți astronauți. |
| `backend/app/security/passwords.py` | gata | Parolele: în baza de date stă doar hash-ul. Fiecare astronaut are parola lui. |
| `backend/app/security/sealing.py` | gata | Sigilarea pachetelor dintre navă și Pământ: semnătură Ed25519 + criptare AES-256-GCM. |
| `backend/app/security/signing.py` | gata | Semnăturile Ed25519 ale măsurătorilor venite de la dispozitive (POST /ingest/measurements). |
| `backend/app/security/tokens.py` | gata | Tokenurile de acces (JWT, HS256). Fiecare token e legat de un singur cont și un singur `crew_id`. |
| `backend/app/security/validation.py` | gata | Validarea măsurătorilor: valori imposibile și senzori „înghețați”. |
| `backend/app/services/__init__.py` | gata | Serviciile: logica aplicației. Routerele le apelează; ele folosesc engine/ (pur), db/, security/, clock. |
| `backend/app/services/access.py` | T08 | Scrierea jurnalului de acces din deps și servicii. TASK T08. |
| `backend/app/services/ai.py` | T31 | Puntea către serviciul AI, cu limită de timp și fallback pe catalog. TASK T31. |
| `backend/app/services/alerts.py` | T30 | Alertele: listă, detaliu, confirmare, pași, escaladare, închidere; recheck_loop (T30). TASK T17. |
| `backend/app/services/auth.py` | T07 | Conturi, login, logout, tokenuri. TASK T07. |
| `backend/app/services/behavioral.py` | T19 | Tastarea (T19) și testul de reacție (T20). TASK T19. |
| `backend/app/services/checkins.py` | T18 | Check-in-ul și decalajul de percepție. TASK T18. |
| `backend/app/services/crew.py` | T21 | Tabloul de bord, panourile pilonilor, seriile, derulatorul (as_of_day). TASK T21. |
| `backend/app/services/demo.py` | T33 | Reset, salt de zi, pachet falsificat, senzor înghețat. TASK T33. |
| `backend/app/services/events.py` | gata | Evenimentele de publicat după commit. Gata, nu e un task (folosit de toate serviciile). |
| `backend/app/services/exercise.py` | T28 | Exercițiile și pilonul Încărcarea. TASK T28. |
| `backend/app/services/link.py` | T23 | Coada din punctul de vedere al API-ului: listă, detaliu, outbox, răspunsul Pământului, mesaje. TASK T23. |
| `backend/app/services/mission.py` | T22 | Starea misiunii, mediile, ceasul; mission_ticker (T22). TASK T09. |
| `backend/app/services/pipeline.py` | T16 | Drumul oricărei date noi: salvare → motor → triaj → alerte → (nivel 3) pachet → evenimente. TASK T16. |
| `backend/app/services/radiation.py` | T25 | Starea radiațiilor, seria, adăpostul, furtuna (T26). TASK T25. |
| `backend/app/services/security_log.py` | T32 | Primirea măsurătorilor, respingerile, dovezile (teste, praguri). TASK T32. |
| `backend/app/simulator/__init__.py` | gata | Simulatorul: datele generate (istoricul de la pornire, datele live, furtuna). Reproductibil: același seed → aceleași date. |
| `backend/app/simulator/devices.py` | T32 | Dispozitivele simulate: trimit măsurători semnate la /ingest/measurements (sau direct prin serviciu). TASK T32. |
| `backend/app/simulator/live.py` | T25 | Datele LIVE, cât ceasul merge. Task din fundal (pas 2 s reale). TASK T25 (radiații) și T33 (salt de zi). |
| `backend/app/simulator/radiation.py` | T25 | Rata dozei de la dozimetru. Forma furtunii e SINTETICĂ; orele vin din fișierul DONKI. TASK T25. |
| `backend/app/simulator/scenario.py` | T10 | Generatorul celor 140 de zile, din data/scenario/scenario.json. TASK T10. |
| `backend/pyproject.toml` | gata | dependențele (uv) |
| `backend/seed/users.json` | gata | conturile de test, câte unul pe astronaut |
| `backend/tests/conftest.py` | gata | Fixture-ul comun (backend/PLAN_DE_ATAC_BACKEND.md, secțiunea 13). |
| `backend/tests/routers/test_contract_basics.py` | mock → — | Teste de bază pe contract. Rămân valabile și după ce mock-ul e înlocuit cu logica reală. |
| `backend/uv.lock` | gata | versiunile exacte (se comite) |
