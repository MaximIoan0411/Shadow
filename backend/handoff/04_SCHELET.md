# 04 — Scheletul backend-ului

**Generat** de `scripts/build_handoff.py`. Fiecare fișier din `backend/`, ce face și taskul care îl implementează.
„gata” = funcționează deja; „mock” = răspunde cu date de exemplu până la taskul indicat; `Txx` = schelet
(semnături + `NotImplementedError("Txx")`).

| Fișier | Stare | Ce face |
|---|---|---|
| `backend/.env` | gata |  |
| `backend/.python-version` | gata | 3.12 |
| `backend/app/ai_schemas.py` | gata | SHADOW — contractul dintre backend și serviciul AI (portul 8001). COPIE a ai/service/schemas.py. |
| `backend/app/clock.py` | gata |  |
| `backend/app/config.py` | gata |  |
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
| `backend/app/db/repos.py` | gata |  |
| `backend/app/db/seed.py` | gata |  |
| `backend/app/db/session.py` | gata | Motorul asincron și sesiunea. Verificat (plan, secțiunea 5). |
| `backend/app/deps.py` | gata |  |
| `backend/app/engine/__init__.py` | gata | Motorul: funcții PURE. Primesc date simple, întorc rezultate simple. NU importă db/, fastapi, clock, security. |
| `backend/app/engine/baseline.py` | gata |  |
| `backend/app/engine/cross_signals.py` | gata |  |
| `backend/app/engine/derived.py` | gata |  |
| `backend/app/engine/perception_gap.py` | gata |  |
| `backend/app/engine/pillars/__init__.py` | gata | Cei patru piloni. Fiecare: funcții pure care primesc serii + baseline + praguri și întorc Finding / PillarScore. |
| `backend/app/engine/pillars/behavioral.py` | gata |  |
| `backend/app/engine/pillars/cardio.py` | gata |  |
| `backend/app/engine/pillars/immune.py` | gata |  |
| `backend/app/engine/pillars/musculoskeletal.py` | gata |  |
| `backend/app/engine/radiation.py` | gata |  |
| `backend/app/engine/triage.py` | gata |  |
| `backend/app/engine/types.py` | gata | Tipurile motorului (separate de tabele și de contract). Gata, nu e un task. |
| `backend/app/ids.py` | gata |  |
| `backend/app/link/__init__.py` | gata | Coada navă ↔ Pământ. Sigilarea (semnătură + criptare) vine din security/sealing.py; replay-ul îl blocăm noi. |
| `backend/app/link/queue.py` | gata |  |
| `backend/app/link/scheduler.py` | gata |  |
| `backend/app/link/windows.py` | gata |  |
| `backend/app/main.py` | gata |  |
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
| `backend/app/services/access.py` | gata |  |
| `backend/app/services/ai.py` | gata |  |
| `backend/app/services/alerts.py` | gata |  |
| `backend/app/services/auth.py` | gata |  |
| `backend/app/services/behavioral.py` | gata |  |
| `backend/app/services/checkins.py` | gata |  |
| `backend/app/services/crew.py` | gata |  |
| `backend/app/services/demo.py` | gata |  |
| `backend/app/services/events.py` | gata | Evenimentele de publicat după commit. Gata, nu e un task (folosit de toate serviciile). |
| `backend/app/services/exercise.py` | gata |  |
| `backend/app/services/link.py` | gata |  |
| `backend/app/services/mission.py` | gata |  |
| `backend/app/services/pipeline.py` | gata |  |
| `backend/app/services/radiation.py` | gata |  |
| `backend/app/services/security_log.py` | gata |  |
| `backend/app/simulator/__init__.py` | gata | Simulatorul: datele generate (istoricul de la pornire, datele live, furtuna). Reproductibil: același seed → aceleași date. |
| `backend/app/simulator/devices.py` | gata |  |
| `backend/app/simulator/live.py` | gata |  |
| `backend/app/simulator/radiation.py` | gata |  |
| `backend/app/simulator/scenario.py` | gata |  |
| `backend/CLAUDE.md` | gata |  |
| `backend/CUM_LUCRAM.MD` | gata |  |
| `backend/jurnal/jurnal_task_T00.md` | gata |  |
| `backend/jurnal/jurnal_task_T01.md` | gata |  |
| `backend/jurnal/jurnal_task_T02.md` | gata |  |
| `backend/jurnal/jurnal_task_T03.md` | gata |  |
| `backend/jurnal/jurnal_task_T04.md` | gata |  |
| `backend/jurnal/jurnal_task_T05.md` | gata |  |
| `backend/jurnal/jurnal_task_T06.md` | gata |  |
| `backend/jurnal/jurnal_task_T07.md` | gata |  |
| `backend/jurnal/jurnal_task_T08.md` | gata |  |
| `backend/jurnal/jurnal_task_T09.md` | gata |  |
| `backend/jurnal/jurnal_task_T10.md` | gata |  |
| `backend/jurnal/jurnal_task_T11.md` | gata |  |
| `backend/jurnal/jurnal_task_T12.md` | gata |  |
| `backend/jurnal/jurnal_task_T13.md` | gata |  |
| `backend/jurnal/jurnal_task_T14.md` | gata |  |
| `backend/jurnal/jurnal_task_T15.md` | gata |  |
| `backend/jurnal/jurnal_task_T16.md` | gata |  |
| `backend/jurnal/jurnal_task_T17.md` | gata |  |
| `backend/jurnal/jurnal_task_T18.md` | gata |  |
| `backend/jurnal/jurnal_task_T19.md` | gata |  |
| `backend/jurnal/jurnal_task_T20.md` | gata |  |
| `backend/jurnal/jurnal_task_T21.md` | gata |  |
| `backend/jurnal/jurnal_task_T22.md` | gata |  |
| `backend/jurnal/jurnal_task_T23.md` | gata |  |
| `backend/jurnal/jurnal_task_T24.md` | gata |  |
| `backend/jurnal/jurnal_task_T25.md` | gata |  |
| `backend/jurnal/jurnal_task_T26.md` | gata |  |
| `backend/jurnal/jurnal_task_T27.md` | gata |  |
| `backend/jurnal/jurnal_task_T28.md` | gata |  |
| `backend/jurnal/jurnal_task_T29.md` | gata |  |
| `backend/jurnal/jurnal_task_T30.md` | gata |  |
| `backend/jurnal/jurnal_task_T31.md` | gata |  |
| `backend/jurnal/jurnal_task_T32.md` | gata |  |
| `backend/jurnal/jurnal_task_T33.md` | gata |  |
| `backend/PLAN_DE_ATAC_BACKEND.md` | gata | planul: arhitectura, regulile, orele |
| `backend/pyproject.toml` | gata | dependențele (uv) |
| `backend/README.md` | gata | cum pornești |
| `backend/seed/users.json` | gata | conturile de test, câte unul pe astronaut |
| `backend/tests/conftest.py` | gata |  |
| `backend/tests/engine/test_baseline.py` | gata |  |
| `backend/tests/engine/test_cardio.py` | gata |  |
| `backend/tests/engine/test_clock.py` | gata |  |
| `backend/tests/engine/test_cross_signals.py` | gata |  |
| `backend/tests/engine/test_immune.py` | gata |  |
| `backend/tests/engine/test_keystrokes.py` | gata |  |
| `backend/tests/engine/test_loading.py` | gata |  |
| `backend/tests/engine/test_perception_gap.py` | gata |  |
| `backend/tests/engine/test_pvt.py` | gata |  |
| `backend/tests/engine/test_radiation.py` | gata |  |
| `backend/tests/engine/test_scenario.py` | gata |  |
| `backend/tests/engine/test_triage.py` | gata |  |
| `backend/tests/link/test_donki_uplink.py` | gata |  |
| `backend/tests/link/test_enqueue.py` | gata |  |
| `backend/tests/link/test_scheduler.py` | gata |  |
| `backend/tests/routers/test_ai_bridge.py` | mock → — |  |
| `backend/tests/routers/test_alerts_api.py` | mock → — |  |
| `backend/tests/routers/test_checkin_api.py` | mock → — |  |
| `backend/tests/routers/test_contract_basics.py` | mock → — | Teste de bază pe contract. Rămân valabile și după ce mock-ul e înlocuit cu logica reală. |
| `backend/tests/routers/test_crew_api.py` | mock → — |  |
| `backend/tests/routers/test_data_startup.py` | mock → — |  |
| `backend/tests/routers/test_db_startup.py` | mock → — |  |
| `backend/tests/routers/test_demo.py` | mock → — |  |
| `backend/tests/routers/test_events.py` | mock → — |  |
| `backend/tests/routers/test_ids.py` | mock → — |  |
| `backend/tests/routers/test_keystrokes_api.py` | mock → — |  |
| `backend/tests/routers/test_mission.py` | mock → — |  |
| `backend/tests/routers/test_pipeline_replay.py` | mock → — |  |
| `backend/tests/routers/test_recheck.py` | mock → — |  |
| `backend/tests/routers/test_repos.py` | mock → — |  |
| `backend/tests/routers/test_seed.py` | mock → — |  |
| `backend/tests/routers/test_seed_history.py` | mock → — |  |
| `backend/tests/security/test_access_log_wiring.py` | gata |  |
| `backend/tests/security/test_auth_flow.py` | gata |  |
| `backend/tests/security/test_ingest.py` | gata |  |
| `backend/tests/test_config.py` | gata |  |
| `backend/uv.lock` | gata | versiunile exacte (se comite) |
