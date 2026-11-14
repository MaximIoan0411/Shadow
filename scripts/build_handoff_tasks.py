"""Generează backend/handoff/tasks/T*.md. Rulează din rădăcină: python3 scripts/build_handoff_tasks.py backend/handoff/tasks"""
import pathlib
import sys

T = []


def task(id, slug, title, who, prio, minutes, depends, goal, read, steps, files, done, dont=(), pitfalls=()):
    T.append(dict(id=id, slug=slug, title=title, who=who, prio=prio, minutes=minutes, depends=depends, goal=goal,
                  read=read, steps=steps, files=files, done=done, dont=dont, pitfalls=pitfalls))


SMOKE = "`uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`"
PYTEST = "`uv run pytest -q` (din `backend/`) → toate trec"

# ---------------------------------------------------------------------------------------------------------- fundație
task("T00", "pornire", "Pornire și verificare", "A+B", "P0", 15, [],
     "Ambii aveți repo-ul pornit local, mock-ul răspunde și toate verificările trec, înainte să scrieți cod.",
     ["`backend/README.md`", "`backend/handoff/04_SCHELET.md`"],
     ["Clonează repo-ul și instalează `uv` (https://docs.astral.sh/uv/).",
      "`cd backend && uv sync`.",
      "`uv run uvicorn app.main:app --reload --port 8000` și deschide http://localhost:8000/docs.",
      "Autentifică-te în Swagger: `POST /api/v1/auth/login` cu `specialist2` / `cm2-shadow`; apoi „Authorize” cu tokenul primit.",
      "Apelează `GET /api/v1/crew/cm-2/dashboard`: vezi alerta imunitară din scenariu.",
      "Rulează testele și verificarea contractului (comenzile de mai jos).",
      "Citește `04_SCHELET.md`: vezi ce e gata, ce e mock și ce e schelet."],
     ["nimic de schimbat"],
     ["`uv run pytest -q` → 5 teste trec", SMOKE, "Swagger se deschide și login-ul merge"],
     dont=["Nu șterge `app/examples.py`: mock-ul trebuie să meargă până la T34."])

task("T01", "setari", "Setările", "A", "P0", 15, ["T00"],
     "Toată configurația vine din `app/config.py` (pydantic-settings, din `.env`), iar `create_app()` o folosește.",
     ["`backend/app/config.py` (există)", "`backend/app/main.py`", "`.env.example` din rădăcină"],
     ["Citește `Settings` din `app/config.py`; câmpurile există deja.",
      "În `create_app()` (`app/main.py`): `settings = get_settings()` la începutul funcției; pune-l în `app.state.settings`.",
      "Înlocuiește lista fixă de la CORS cu `settings.cors_origins`.",
      "Creează `backend/.env` din exemplu doar local (nu se comite).",
      "Scrie testul: cu `monkeypatch.setenv(\"TIME_SCALE\", \"7\")`, `create_app().state.settings.time_scale == 7`."],
     ["`app/main.py`", "`tests/test_config.py` (nou)"],
     [PYTEST, SMOKE, "`grep -rn \"os.environ\" app/` nu găsește nimic în afară de `datafiles.py`"],
     dont=["Nu citi setările la import (`settings = Settings()` la nivel de modul): testele trebuie să le poată schimba."])

task("T02", "ceasul", "Ceasul misiunii (SimClock)", "A", "P0", 30, ["T00"],
     "`app/clock.py` dă timpul misiunii: pornește în ziua 96 la 07:00 și merge de `scale` ori mai repede decât timpul real.",
     ["`backend/app/clock.py` (schelet)", "`data/scenario/scenario.json` (start, start_day, start_time)"],
     ["Implementează `SimClock` cu trei câmpuri interne: `_real0` (`time.monotonic()` la pornire), `_sim0` (data misiunii la pornire), `_scale`.",
      "`now() = _sim0 + timedelta(seconds=(monotonic() - _real0) * _scale)`, cu `tzinfo=UTC`.",
      "`mission_day(at)` = `(at - mission_start).days + 1`; `day_start(day)` = `mission_start + (day - 1) zile`.",
      "`start(mission_start, day, time_hhmm, scale)`: `_sim0 = day_start(day) + ora`.",
      "`set_scale`: fixează `_sim0 = now()`, `_real0 = monotonic()`, apoi schimbă viteza (ora nu sare).",
      "`jump_to_day(day)`: `ValueError` dacă `day <= mission_day()`; altfel mută `_sim0` la ziua aceea.",
      "`real_seconds(s) = s / scale`; `freeze(at)`: `now()` întoarce `at` până la următorul `start`.",
      "Teste în `tests/engine/test_clock.py`: ziua 96 la pornire; ×60 → 1 s real = 60 s de misiune (cu `freeze` sau monkeypatch pe `time.monotonic`); `set_scale` nu sare; `jump_to_day` înapoi dă `ValueError`."],
     ["`app/clock.py`", "`tests/engine/test_clock.py` (nou)"],
     [PYTEST, "`grep -rn \"datetime.now\\|datetime.utcnow\" app/` nu găsește nimic în codul nou"],
     dont=["Nu folosi `time.time()` (se poate schimba); folosește `time.monotonic()`."],
     pitfalls=["`mission_start` vine din `data.scenario.start` (2027-01-10T00:00Z), nu din cod."])

task("T03", "baza-la-pornire", "Baza de date la pornire", "A", "P0", 30, ["T01"],
     "La pornire, `lifespan` șterge baza veche, creează motorul și toate tabelele; endpoint-urile pot cere o sesiune cu `Depends(get_session)`.",
     ["`backend/app/main.py` (lifespan)", "`backend/app/db/session.py` (gata)", "`backend/app/db/models/` (gata)", "`handoff/03_BAZA_DE_DATE.md`"],
     ["În `lifespan`: dacă `settings.reset_db_on_start`, șterge fișierul SQLite și `-wal`, `-shm` (funcția `delete_sqlite_files` e în plan, secțiunea 6).",
      "`engine = db.init_engine(settings.database_url)`; `import app.db.models` (înregistrează tabelele); `await conn.run_sync(Base.metadata.create_all)`.",
      "La oprire: `await engine.dispose()`.",
      "`/health`: întoarce și `\"db\": \"ok\"` după un `SELECT 1` (câmp nou, opțional — contractul permite).",
      "Test: după pornirea aplicației (fixture-ul `client`), fișierul SQLite există și are 16 tabele (`sqlalchemy.inspect`)."],
     ["`app/main.py`", "`tests/routers/test_db_startup.py` (nou)"],
     [PYTEST, SMOKE, "`uv run uvicorn app.main:app` pornește de două ori la rând fără eroare (baza se recreează)"],
     dont=["Nu adăuga Alembic.", "Nu importa `SessionLocal` direct (`from app.db.session import SessionLocal` dă `None`)."])

task("T04", "id-uri", "Id-urile cu prefix", "A", "P0", 20, ["T03"],
     "`next_id(session, \"al\")` dă `al-0001`, `al-0002`…, iar `next_seq(session, \"down\")` dă 1, 2…, cu contorul în `sim_state`, în aceeași tranzacție.",
     ["`backend/app/ids.py` (schelet)", "`backend/app/db/models/sim.py`"],
     ["Citește rândul `id:<prefix>` din `sim_state` (`session.get(SimState, key)`); dacă lipsește, pornește de la 0.",
      "Crește `n`, scrie înapoi (**atribuie un dict nou**, nu modifica dict-ul pe loc: JSON-ul nu se detectează ca schimbat).",
      "Formatează cu `WIDTH` cifre: `f\"{prefix}-{n:0{WIDTH}d}\"`.",
      "`next_seq` la fel, cu cheia `seq:<direction>`.",
      "Teste: trei apeluri dau 0001, 0002, 0003; prefixe diferite au contoare separate; după rollback contorul nu a crescut."],
     ["`app/ids.py`", "`tests/routers/test_ids.py` (nou)"],
     [PYTEST],
     pitfalls=["`sim_state.value[\"n\"] += 1` NU se salvează: SQLAlchemy nu vede schimbările în interiorul unui JSON. Atribuie `row.value = {\"n\": n}`."])

task("T05", "date-la-pornire", "Datele din data/ la pornire", "B", "P0", 20, ["T03"],
     "La pornire, `load_all()` încarcă și validează tot `data/`; rezultatul stă în `app.state.data`, iar serviciile îl primesc printr-o dependență.",
     ["`backend/app/datafiles.py` (gata)", "`contract/data/README.md`", "`backend/app/engine/types.py`, `engine/derived.py` (gata)"],
     ["În `lifespan`, după baza de date: `app.state.data = load_all(settings.data_dir)` (relativ la `backend/`).",
      "În `app/deps.py`: `def get_data(request: Request) -> DataBundle: return request.app.state.data`.",
      "Adaugă `app.state.keys = security.keys.load_keys(link_aes_key_b64=settings.link_aes_key_b64)`.",
      "Test: `DATA_DIR` spre un folder gol → pornirea aplicației aruncă `DataError` cu lista fișierelor lipsă.",
      "Test: `get_data` întoarce `params.value(\"nightsignal_red_delta_bpm\") == 4`."],
     ["`app/main.py`", "`app/deps.py`", "`tests/routers/test_data_startup.py` (nou)"],
     [PYTEST, SMOKE, "`uv run --project backend python scripts/validate_data.py` → OK"],
     dont=["Nu copia pragurile în cod: se citesc din `params`."])

task("T06", "seed-conturi", "Seed: echipaj și conturi", "A", "P0", 30, ["T03", "T04"],
     "La pornire există cei 4 membri ai echipajului și cele 5 conturi din `backend/seed/users.json`, cu parolele doar ca hash.",
     ["`backend/app/db/seed.py` (schelet)", "`backend/seed/users.json`", "`backend/app/security/passwords.py`", "`handoff/03_BAZA_DE_DATE.md` (crew, users)"],
     ["`seed_crew_and_users`: citește JSON-ul; creează `Crew` pentru fiecare cont cu `crew_id` (titlul rolului: din `display_name` sau o hartă mică).",
      "`await session.flush()` după echipaj (cheile străine!).",
      "Pentru fiecare cont: `password_hash = await asyncio.to_thread(passwords.hash, u[\"test_password\"])`; creează `User`.",
      "Apelează funcția din `lifespan`, în `async with db.SessionLocal() as s:` + `await s.commit()`.",
      "Test: după pornire, `users` are 5 rânduri, `crew` 4, iar niciun `password_hash` nu conține parola în clar."],
     ["`app/db/seed.py`", "`app/main.py`", "`tests/routers/test_seed.py` (nou)"],
     [PYTEST, SMOKE],
     pitfalls=["Hash-ul e lent intenționat (~50 ms): 5 conturi sunt OK; nu-l apela fără `to_thread`."])

task("T07", "autentificare", "Autentificarea reală", "A", "P0", 60, ["T06"],
     "Login, conturi, `me` și logout lucrează cu baza de date și tokenuri reale; `deps.current_user` decodează tokenul. Tokenurile `mock-<utilizator>` rămân acceptate cât `ALLOW_MOCK_TOKENS=true` (testele și frontend-ul pe mock).",
     ["`backend/app/routers/auth.py`", "`backend/app/deps.py`", "`backend/app/services/auth.py` (schelet)", "`contract/security/README.md`", "`handoff/02_CONTRACT_ENDPOINTS.md` (T07)"],
     ["`services/auth.list_accounts`: conturile din bază → `LoginAccount` (`location = \"earth\"` pentru rolul earth).",
      "`services/auth.login`: ordinea din `contract/security/README.md` §2: `lockout.check` → `passwords.verify` (cu `DUMMY_HASH` dacă nu există) → `record_failure`/`clear` → `tokens.issue(secret=settings.jwt_secret)` → `access_log.write(login | login_failed)`.",
      "`AccountLocked` → `ApiError(429, \"too_many_attempts\", …, {\"retry_after_s\": …})`; parolă greșită → `ApiError(401, \"invalid_credentials\", \"Utilizator sau parolă greșită.\")`.",
      "`services/auth.user_from_token`: `mock-<u>` (dacă e permis) sau `tokens.decode` + `tokens.is_revoked` + contul din bază → `schemas.User`; `InvalidToken` → 401 `unauthorized`.",
      "`deps.current_user` devine `async` și primește sesiunea + setările; restul dependențelor (`require_roles`, `crew_access`) rămân la fel.",
      "`logout`: `tokens.revoke(session, claims.jti, expires_at)` + `access_log.write(logout)`.",
      "Routerul `auth.py`: corpurile apelează serviciul; scoate `_HASHES` și citirea din `examples.USERS`.",
      "Teste: login corect dă un token real care merge la `/auth/me`; după logout același token dă 401; parola altui cont dă 401; 5 greșeli dau 429; `mock-specialist2` merge cu `ALLOW_MOCK_TOKENS=true` și dă 401 cu `false`."],
     ["`app/services/auth.py`", "`app/routers/auth.py`", "`app/deps.py`", "`tests/security/test_auth_flow.py` (nou)"],
     [PYTEST, SMOKE + " (smoke folosește tokenuri mock)", "`role` și `crew_id` vin doar din token, nu din cerere"],
     dont=["Nu scrie criptografie: folosește `security/tokens.py`, `passwords.py`, `lockout.py`.",
           "Nu schimba forma răspunsului `LoginResponse`."],
     pitfalls=["`current_user` devenit `async` cu `Depends(get_session)`: FastAPI le înlănțuie singur; nu deschide sesiuni manual în dependență."])

task("T08", "jurnal-acces", "Jurnalul de acces", "A", "P1", 30, ["T07"],
     "Accesurile importante lasă urmă în `access_log`, iar `GET /access-log` le citește din bază.",
     ["`backend/app/security/access_log.py`", "`backend/app/deps.py` (crew_access)", "`backend/app/routers/security.py` (access_log)", "`backend/app/services/access.py` (schelet)"],
     ["În `crew_access`: dacă un `cmo` citește datele altui membru → `access_log.write(action=\"read_dashboard\" sau după cale, outcome=\"allowed\")`; orice 403 → `outcome=\"denied\"`, `action=\"access_denied\"`.",
      "În `GET /alerts/{id}` citit de `cmo` → `read_alert`.",
      "`GET /access-log`: astronautul vede doar intrările cu `crew_id` al lui; `cmo` tot; cele mai noi primele; `limit`.",
      "Notă: până la varianta reală a securității, `access_log.write` ține totul în memorie; dacă vrei să-l vezi în bază, cere echipei de securitate varianta cu `INSERT` (semnătura e aceeași).",
      "Test: comandantul cere `/crew/cm-2/dashboard` → 403 și o intrare `denied` în jurnal; `medic` citește → intrare `allowed`."],
     ["`app/deps.py`", "`app/routers/security.py`", "`app/services/access.py`", "`tests/security/test_access_log_wiring.py` (nou)"],
     [PYTEST, SMOKE],
     dont=["Nu scrie parole sau tokenuri în jurnal."])

task("T09", "misiunea", "Misiunea și mediile", "A", "P0", 40, ["T02", "T05"],
     "`/mission`, `/environments`, `PUT /mission/environment` și `PUT /sim/clock` (doar viteza) folosesc ceasul și `data/environments.json`; mediul curent stă în `sim_state`.",
     ["`backend/app/routers/mission.py`", "`backend/app/services/mission.py` (schelet)", "`data/environments.json`", "`handoff/02_CONTRACT_ENDPOINTS.md` (T09)"],
     ["La pornire (lifespan): `clock.start(mission_start=data.scenario.start, day=data.scenario.start_day, time_hhmm=data.scenario.start_time, scale=settings.time_scale)` și `sim_state[\"environment\"] = {\"id\": data.environments.default}`.",
      "`services/mission.state(session, data)` → `MissionState`: `sim_now = clock.now()`, `mission_day`, `total_days`, `time_scale`, mediul curent (`EnvironmentInfo` din fișier), `LinkStatus` (întârzierea și `one_way_delay_real_s = clock.real_seconds(...)`; `queued_down`/`queued_up` = numărul pachetelor `queued` din bază).",
      "`PUT /mission/environment`: scrie în `sim_state`; întoarce noul `MissionState`; evenimentul `environment.changed` după commit.",
      "`PUT /sim/clock`: `time_scale` → `clock.set_scale`; `mission_day` rămâne mock până la T33 (dar regula 409 înapoi rămâne).",
      "Teste: `/mission` dă ziua 96; după `PUT environment iss`, `link.one_way_delay_s == 1`; `time_scale` se schimbă fără să sară ora."],
     ["`app/services/mission.py`", "`app/routers/mission.py`", "`app/main.py`", "`tests/routers/test_mission.py` (nou)"],
     [PYTEST, SMOKE])

# ---------------------------------------------------------------------------------------------------------- simulator + motor
task("T10", "generator-scenariu", "Simulatorul: generatorul de scenariu", "B", "P0", 75, ["T05"],
     "`simulator/scenario.generate()` produce, PUR (fără bază), datele zilelor cerute pentru toți membrii, după `data/scenario/scenario.json`, la fel la fiecare rulare.",
     ["`backend/app/simulator/scenario.py` (schelet)", "`data/scenario/scenario.json`", "`backend/app/datafiles.py` (ScenarioFile)", "`docs/BACKEND_SARCINI.md` §4 (tabelul evenimentelor)"],
     ["Pentru fiecare zi și membru: `rng = random.Random(scenario.seed * 1000 + day * 10 + nr_membru)` (determinist pe zi, nu pe interval).",
      "Valori zilnice din `crew_baselines[crew]` + zgomot mic: `night_pulse_bpm` (03:00, zgomot ≤ `noise_max_bpm` = 0,8), `resting_pulse_bpm`, `hrv_lnrmssd`, `temperature_c`, `sleep_hours`, `systolic/diastolic_mmhg`, `glucose_mg_dl`.",
      "Check-in zilnic la 07:00 (dispoziția 4 de obicei, cu mici variații) cu valorile manuale.",
      "Exerciții: 2 sesiuni de rezistență (09:00 și 16:00) în zilele normale.",
      "O sesiune de tastare pe zi (07:15) cu trăsăturile din baseline (`keys_per_min`, `hold_ms_mean`) — pentru baseline-ul tastării.",
      "Aplică evenimentele: `poor_sleep` (somn −1,6 h, tastare −10% pentru toți), `skipped_exercise` (0 sesiuni), `infection_onset` (pulsul de noapte + `night_pulse_bpm_delta_by_day`, temperatură +0,4, somn −1,1), `keystroke_slowdown` (tastare −18%, hold +17%, dispoziția 4), `cardio_deconditioning` (puls de repaus în sus, HRV în jos).",
      "`solar_storm` NU se generează aici (e live, T25).",
      "Teste în `tests/engine/test_scenario.py`: două rulări dau exact aceleași date; `generate(…, 94, 94)` == ziua 94 din `generate(…, 1, 96)`; pulsul de noapte al lui cm-2: ziua 93 < baseline+3, ziua 94 ≥ baseline+4, ziua 95 ≥ baseline+4; ziua 61 nu are exerciții pentru cm-2."],
     ["`app/simulator/scenario.py`", "`tests/engine/test_scenario.py` (nou)"],
     [PYTEST],
     dont=["Nu scrie în bază aici (e T11).", "Nu scrie evenimentele în cod: vin din `scenario.events`."],
     pitfalls=["Zgomotul mare ar muta zilele alertei. Păstrează zgomotul pulsului de noapte sub 0,8 bpm."])

task("T11", "seed-istoric", "Seed: istoricul zilelor 1–96", "B", "P0", 45, ["T06", "T10"],
     "La pornire, zilele 1–96 ajung în bază: măsurători, check-in-uri, exerciții și sesiunile de tastare, marcate `simulated`.",
     ["`backend/app/db/seed.py` (schelet)", "`backend/app/simulator/scenario.py`", "`handoff/03_BAZA_DE_DATE.md` (measurements, checkins, exercise_sessions, keystroke_sessions)"],
     ["`days = await asyncio.to_thread(scenario.generate, data.scenario, from_day=1, to_day=until_day)`.",
      "Transformă în obiecte ORM (`Measurement`, `Checkin` cu `source=\"simulated\"`, `ExerciseSession`, `KeystrokeSession` cu `is_baseline=True` pentru primele `keystroke_baseline_duration` zile).",
      "Id-uri: `next_id` pentru check-in-uri (`ck`) și exerciții (`ex`); măsurătorile au id întreg automat.",
      "`session.add_all(...)` o singură dată, apoi commit (nu rând cu rând).",
      "Apelează din `lifespan` după seed-ul conturilor; măsoară durata (țintă: tot `lifespan` sub 10 s).",
      "Test: după pornire, cm-2 are 96 de check-in-uri și pulsul de noapte pentru zilele 1–96."],
     ["`app/db/seed.py`", "`app/main.py`", "`tests/routers/test_seed_history.py` (nou)"],
     [PYTEST, SMOKE, "pornirea durează sub 10 s (log-ul spune cât)"],
     pitfalls=["`next_id` de ~600 de ori într-o buclă e lent dacă faci `flush` după fiecare; ține contorul local și scrie `sim_state` o dată la final."])

task("T12", "baseline", "Motor: baseline-ul personal", "B", "P0", 30, ["T05"],
     "`engine/baseline.compute()` calculează normalul personal (mediana + deviația robustă) dintr-o serie, fără zilele în alertă.",
     ["`backend/app/engine/baseline.py` (schelet)", "`backend/app/engine/types.py`", "`backend/app/engine/derived.py` (MIN_SPREAD)"],
     ["Filtrează punctele: fără `exclude_days`; doar ultimele `window_days` (dacă e dat).",
      "`median` = mediana valorilor; `spread = max(1.4826 × MAD, min_spread)`; `n`; `ready = n >= min_n`.",
      "Serie goală → `Baseline(median=nan, spread=min_spread, n=0, ready=False)`.",
      "`deviation(value, base) = (value - base.median) / base.spread`.",
      "Teste în `tests/engine/test_baseline.py`: valori constante → spread = min_spread; un vârf izolat nu mută mediana; zilele excluse nu contează; `ready` la `min_n`."],
     ["`app/engine/baseline.py`", "`tests/engine/test_baseline.py` (nou)"],
     ["`uv run pytest tests/engine -q`"],
     dont=["Nu importa nimic din `db/` sau `fastapi`."])

task("T13", "repos", "Interogările refolosite (repos)", "B", "P0", 30, ["T11"],
     "`db/repos.py` dă seriile pe zile pentru motor și pentru grafice, ca tipuri `Point`, fără ca motorul să știe de SQLAlchemy.",
     ["`backend/app/db/repos.py` (schelet)", "`backend/app/engine/types.py` (Point)", "`handoff/03_BAZA_DE_DATE.md` (measurements, indexul ix_meas_crew_metric_day)"],
     ["`series`: `select(Measurement).where(crew_id, metric_key, mission_day between).order_by(mission_day, measured_at)`; păstrează ultima valoare pe zi.",
      "Metricile din check-in (`temperature_c`, `sleep_hours`, `systolic_mmhg`…) vin din `checkins` dacă nu sunt în `measurements`: tratează-le printr-o hartă `CHECKIN_METRICS`.",
      "`series_all_crew`, `latest`, `recent_device_values` după aceeași idee.",
      "Teste: `series(cm-2, night_pulse_bpm, 90, 96)` are 7 puncte crescătoare; o metrică de check-in merge la fel."],
     ["`app/db/repos.py`", "`tests/routers/test_repos.py` (nou)"],
     [PYTEST])

task("T14", "santinela", "Pilonul Santinela (NightSignal)", "B", "P0", 45, ["T12", "T13"],
     "Regula NightSignal (Alavi et al. 2022) pe pulsul de noapte, față de mediana personală: galben la o noapte ≥ +3 bpm, roșu la două nopți la rând ≥ +4 bpm. Plus indicele de stres și scorul pilonului.",
     ["`backend/app/engine/pillars/immune.py` (schelet)", "`data/parameters.json`: `nightsignal_yellow_delta`, `nightsignal_red_delta_bpm`, `nightsignal_red_consecutive_nights`, `nightsignal_min_nights_baseline`", "`data/catalog/recommendations.json`: `immune-1-1`, `immune-2-1`"],
     ["Baseline-ul: nopțile **de dinainte** de cea evaluată (fără zilele cu alertă imunitară), `min_n = nightsignal_min_nights_baseline` (7).",
      "Delta = pulsul nopții − mediana.",
      "Roșu: ultimele `red_nights` (2) nopți toate ≥ `red_delta` (4) → `Finding(level=2, status=\"alert\", recommendation_id=\"immune-2-1\")`.",
      "Altfel galben: ultima noapte ≥ `yellow_delta` (3) → `Finding(level=1, status=\"watch\", recommendation_id=\"immune-1-1\")`.",
      "Titlul în română cu cifrele: „Puls de noapte +7 bpm, 3 nopți la rând”; dovezile (`EvidenceItem`) pentru puls, temperatură și somn.",
      "`stress_index`: 0..100 (o combinație simplă, documentată în docstring); `score`: 100 − penalizare după delta.",
      "Teste în `tests/engine/test_immune.py` cu serii scrise de mână: o noapte +4 → galben; două nopți +4 → roșu; +3,9 și +4 → nu roșu; baseline-ul nu e gata (5 nopți) → None; **și pe scenariu**: cm-2 galben în ziua 94, roșu în ziua 95."],
     ["`app/engine/pillars/immune.py`", "`tests/engine/test_immune.py` (nou)"],
     ["`uv run pytest tests/engine/test_immune.py -q`", "testul `test_nightsignal_red_after_two_nights` există (apare în ecranul Evidence)"],
     dont=["Nu scrie pragurile în cod: le primești ca parametri."])

task("T15", "triaj", "Motor: triajul", "B", "P0", 30, ["T14"],
     "`engine/triage.decide()` transformă constatările în decizii: creează o alertă nouă, o actualizează sau o escaladează; nivelul nu coboară niciodată.",
     ["`backend/app/engine/triage.py` (schelet)", "`backend/app/engine/types.py` (Finding, TriageDecision)"],
     ["Pentru fiecare `Finding`: cheia `(crew_id, topic)`.",
      "Fără alertă deschisă → `create`.",
      "Cu alertă deschisă la nivel ≥ al constatării → `update` (textele și dovezile se actualizează, nivelul rămâne).",
      "Cu alertă deschisă la nivel mai mic → `escalate` cu `new_level`.",
      "Teste în `tests/engine/test_triage.py`: cele trei cazuri + două constatări pe același subiect în același apel → o singură decizie (cea mai gravă)."],
     ["`app/engine/triage.py`", "`tests/engine/test_triage.py` (nou)"],
     ["`uv run pytest tests/engine -q`"])

task("T16", "pipeline", "Drumul unei date + replay la pornire", "B", "P0", 75, ["T15"],
     "`services/pipeline.process()` e drumul oricărei date noi: motorul pilonilor afectați → triaj → alerte în bază (cu pașii din catalog și istoricul). La pornire, `replay_history` rulează același drum pe zilele 1–96, deci alerta lui cm-2 o produce motorul.",
     ["`backend/app/services/pipeline.py` (schelet)", "`backend/app/engine/triage.py`, `pillars/immune.py`", "`backend/app/db/models/alerts.py`", "`data/catalog/recommendations.json` (steps, recheck_days)", "`backend/app/services/events.py`"],
     ["Hartă `PILLAR_OF_METRIC`: `night_pulse_bpm`, `temperature_c`, `sleep_hours` → immune; tastare/pvt → behavioral; etc. Rulează doar pilonii atinși de `changed`.",
      "Încarcă alertele deschise ale membrului (`state != \"resolved\"`).",
      "Pentru `create`: `Alert` cu `next_id(\"al\")`, `state=\"active\"`, `recommendation_id`, pașii din `catalog.steps` (sau propozițiile din `action`), `recheck_at = acum + recheck_days`, istoricul `created`.",
      "Pentru `update`/`escalate`: actualizează titlul, explicația, dovezile, `updated_at`; la escaladare `level`, `state=\"escalated\"`, istoric `escalated` cu actorul „SHADOW”.",
      "Nivel 3 → pachet spre Pământ: lasă un `# TODO T23` (coada vine mai târziu).",
      "Întoarce evenimentele `alert.created` / `alert.updated` / `dashboard.changed` (cu `crew_id`); NU le publica aici.",
      "`replay_history`: pentru fiecare zi 1..96, cu ceasul „pus” pe ziua aceea (dă data ca parametru, nu muta ceasul), rulează `process` pe toți membrii; fără evenimente (nimeni nu ascultă la pornire).",
      "Apelează `replay_history` în `lifespan` după `seed_history`.",
      "Teste: după pornire există o alertă `immune` pentru cm-2 creată în ziua 94 (nivel 1) și escaladată în ziua 95 (nivel 2); niciun alt membru nu are alertă imunitară."],
     ["`app/services/pipeline.py`", "`app/main.py`", "`tests/routers/test_pipeline_replay.py` (nou)"],
     [PYTEST, SMOKE, "pornirea rămâne sub 10 s"],
     pitfalls=["Încărcarea alertelor cu pașii: `selectinload(Alert.steps), selectinload(Alert.history)`.",
               "În replay, „acum” e ziua reluată: dă-l ca parametru `day`/`at`, nu folosi `clock.now()`."])

task("T17", "alerte-api", "Alertele: endpoint-urile reale", "A", "P0", 60, ["T16"],
     "Toate endpoint-urile de alerte și catalog lucrează cu baza: listă, coada ofițerului medical, detaliu, confirmare, pași, escaladare, închidere.",
     ["`backend/app/routers/alerts.py` (mock)", "`backend/app/services/alerts.py` (schelet)", "`handoff/02_CONTRACT_ENDPOINTS.md` (T17)", "`contract/api/README.md` §4 (cine are voie) și §7.6"],
     ["`services/alerts.to_schema(alert)` → `schemas.Alert` (cu `recommendation` din catalog, pașii, istoricul).",
      "Liste: `GET /crew/{id}/alerts` (filtre `state`, `topic`; cele mai grave primele; `cmo` vede la alții doar nivel ≥ 2); `GET /cmo/queue` (nivel ≥ 2, nerezolvate).",
      "`ack`: doar din `active`, altfel 409 `invalid_state`; istoric `acknowledged`.",
      "Pași: `PUT …/plan/steps/{step_id}` bifează/debifează; istoric `step_done`.",
      "`escalate`: regulile din router (astronautul nu poate la 3 → 403; nivelul nu coboară → 409). La 3: `# TODO T23` pentru pachet (completezi în T23).",
      "`resolve`: astronautul doar nivel 1; `monitoring` mută `recheck_at` cu o zi.",
      "Catalogul: din `app.state.data.catalog`, nu din mock.",
      "Fiecare acțiune: commit, apoi `alert.updated` (`publish_all`).",
      "Teste: firul ack → step → escalate la 2 (astronaut) → escalate la 3 (cmo) → resolve (cmo); erorile 403/409."],
     ["`app/services/alerts.py`", "`app/routers/alerts.py`", "`tests/routers/test_alerts_api.py` (nou)"],
     [PYTEST, SMOKE],
     dont=["Nu schimba `response_model` sau codurile de eroare ale routerului."])

task("T18", "checkin", "Check-in și decalajul de percepție", "A", "P0", 60, ["T16"],
     "Check-in-ul de dimineață se salvează (unul pe zi; câmpurile imposibile respinse, nu eroare), iar decalajul de percepție se calculează din dispoziție și scorurile obiective.",
     ["`backend/app/routers/checkin.py` (mock)", "`backend/app/services/checkins.py`, `engine/perception_gap.py` (schelet)", "`data/texts/checkin_indicators.json` (min/max)", "`engine/derived.py` (PERCEPTION_GAP_*)"],
     ["`GET /checkin/schema`: direct din `data.checkin`.",
      "`POST`: pentru fiecare câmp numeric în afara `min`/`max` → `FieldRejection(reason=\"implausible\")` și `null`; aceeași valoare exactă 3 zile la rând → `frozen_sensor`.",
      "Al doilea check-in în aceeași zi îl **înlocuiește** pe primul (update pe `(crew_id, mission_day)`).",
      "`engine/perception_gap.compute`: `self = mood × 20`; `objective` = media scorurilor disponibile (tastare, pvt, puls de noapte, somn); `gap = self − objective`; `watch` ≥ 15, `alert` ≥ 25; explicația în română cu cifrele.",
      "Rulează `pipeline.process(…, changed={\"temperature_c\", \"sleep_hours\", …})`; întoarce `alerts_created`.",
      "Seria de zile (`Streak` `checkin`): zile consecutive cu check-in până azi.",
      "Evenimente după commit: `dashboard.changed` (`reason=\"checkin\"`), `alert.created`.",
      "Teste: 41,9 °C → în `rejected`, restul salvat; al doilea POST înlocuiește; în ziua 96, dispoziția 4 dă `gap ≥ 25` și `status=\"alert\"` pentru cm-2 (după T19 pentru scorul tastării; până atunci testul folosește scorurile disponibile)."],
     ["`app/services/checkins.py`", "`app/engine/perception_gap.py`", "`app/routers/checkin.py`", "`tests/engine/test_perception_gap.py`, `tests/routers/test_checkin_api.py` (noi)"],
     [PYTEST, SMOKE],
     pitfalls=["Răspunsul la o valoare imposibilă e tot **201**, nu 422."])

task("T19", "tastare", "Tastarea", "B", "P0", 60, ["T16"],
     "Loturile de apăsări (doar timpi și clasa tastei) se adună într-o sesiune; se calculează trăsăturile, abaterea față de baseline și indicele de oboseală.",
     ["`backend/app/routers/behavioral.py` (mock)", "`backend/app/engine/pillars/behavioral.py` (schelet)", "`backend/app/db/models/measurements.py` (KeystrokeSession: acumulatorii)", "`engine/derived.py` (FLIGHT_PAUSE_MS, KEYSTROKE_*)"],
     ["`accumulate`: hold = up − down; flight = down(curent) − down(anterior), sărind pauzele > 2 s; `last_down_ms` leagă loturile; actualizează sume și sume de pătrate; recalculează mediile, deviațiile, `backspace_rate`, `keys_per_min` (din `active_ms`).",
      "Baseline-ul tastării: media trăsăturilor sesiunilor cu `is_baseline=True` ale contului; `baseline_ready` după `keystroke_baseline_duration` sesiuni.",
      "`fatigue_index`: z-scorurile hold (în sus) și viteză (în jos) cântăresc cel mai mult; 0..100; status după `KEYSTROKE_*`.",
      "`POST …/keystrokes/batches` → `KeystrokeResult`; dacă status ≥ watch → `pipeline.process(changed={\"keys_per_min\"})`.",
      "`GET …/keystrokes/summary`: baseline, sesiunea curentă, ultimele `last` sesiuni.",
      "Teste: două loturi cu același `session_id` dau aceleași trăsături ca un singur lot cu toate apăsările; o pauză de 5 s nu intră în flight; o sesiune mai lentă cu 20% dă `fatigue_index` vizibil mai mare."],
     ["`app/engine/pillars/behavioral.py`", "`app/services/behavioral.py`", "`app/routers/behavioral.py`", "`tests/engine/test_keystrokes.py` (nou)"],
     [PYTEST, SMOKE, "în bază nu există niciun caracter tastat (doar numere)"],
     dont=["Nu adăuga un câmp pentru caracter: modelul `KeyEvent` îl respinge intenționat."])

task("T20", "pvt", "Testul de reacție (PVT-B)", "B", "P1", 30, ["T19"],
     "Rezultatul testului de 3 minute: viteza medie (1/RT), lapsusurile (RT ≥ 355 ms), abaterea față de baseline, cu primele teste ca antrenament.",
     ["`backend/app/engine/pillars/behavioral.py` (pvt_summary, pvt_finding)", "`data/parameters.json`: `pvtb_lapse_threshold`, `pvt_reliable_change_derived`, `pvt_practice_runs`"],
     ["`pvt_summary`: ignoră încercările cu `false_start` din RT; `rt_ms = null` = lapsus; `mean_speed = media(1000 / rt_ms)`.",
      "Primele `pvt_practice_runs[1]` (3) teste ale contului: `is_practice=True`, fără baseline și fără alertă.",
      "`deviation_sd = (speed − base_speed) / base_sd`; ≤ −1,24 → `watch` și un `Finding` behavioral nivel 1 (`behavioral-1-1`).",
      "`POST …/pvt` salvează și întoarce `PvtResult`; `GET …/pvt` istoricul.",
      "Teste: lapsus la 355 ms exact; un test lent după 5 teste normale dă `watch`."],
     ["`app/engine/pillars/behavioral.py`", "`app/services/behavioral.py`", "`app/routers/behavioral.py`", "`tests/engine/test_pvt.py` (nou)"],
     [PYTEST, SMOKE])

task("T21", "tablou-de-bord", "Tablou de bord, panouri, derulator", "A", "P0", 75, ["T17", "T18"],
     "Răspunsurile mari pentru interfață (`dashboard`, panoul pilonului, seria, derulatorul, lista echipajului) se construiesc din bază și din motor, inclusiv pentru o zi trecută (`as_of_day`).",
     ["`backend/app/routers/crew.py` (mock)", "`backend/app/services/crew.py` (schelet)", "`data/texts/body_functions.json`", "`handoff/02_CONTRACT_ENDPOINTS.md` (T21)", "`contract/api/README.md` §7.2 și §7.8"],
     ["`dashboard(crew_id, as_of_day)`: scorurile celor 4 piloni (motorul fiecăruia, pe datele până la ziua cerută), decalajul de percepție (check-in-ul zilei), alerta principală (cea mai gravă deschisă), semnalele încrucișate (gol până la T29), seriile, reamintirile zilei, `radiation_alert_active`, `checkin_done_today`.",
      "Pilonii neimplementați încă (Inima, Încărcarea) rămân pe valorile din mock, marcate `data_is_simulated` (le completezi după T27/T28).",
      "Panoul: textele din `body_functions.json`, valorile cu baseline-ul (`MetricValue`), graficul pe ultimele 10 zile cu banda și pragul, planul alertei deschise, sursele din `parameters.json`.",
      "`series`: `?metric&from_day&to_day` din `repos.series`.",
      "`timeline`: starea fiecărui pilon pe fiecare zi până la ziua curentă (din alertele existente pe zile — ieftin; nu rula motorul pe 96 de zile la fiecare cerere).",
      "`GET /crew` (cmo): doar starea generală și numărul de alerte.",
      "`as_of_day` > ziua curentă → 422 (regula există; păstreaz-o).",
      "Teste: cm-2 are zona imunitară `alert`, cm-1 toate `ok`; `as_of_day=93` arată Santinela `ok` pentru cm-2; `timeline` are 96 de zile."],
     ["`app/services/crew.py`", "`app/routers/crew.py`", "`tests/routers/test_crew_api.py` (nou)"],
     [PYTEST, SMOKE, "răspunsul `dashboard` sub ~200 ms local"],
     pitfalls=["Nu calcula motorul pe tot istoricul la fiecare cerere; folosește ce e în bază (alerte, măsurători) și calculează doar ziua cerută."])

task("T22", "evenimente-live", "Evenimentele live", "A", "P0", 30, ["T16"],
     "`/events` trimite `mission.tick` din ceasul real al misiunii la o secundă, `: ping` la 15 secunde, iar toate serviciile publică doar după commit.",
     ["`backend/app/routers/events.py`", "`backend/app/deps.py` (publish, subscribe)", "`backend/app/services/mission.py` (mission_ticker)", "`backend/app/services/events.py`"],
     ["`mission_ticker`: buclă cu `await asyncio.sleep(1)`; `publish(\"mission.tick\", {\"sim_now\": clock.now(), \"mission_day\": …})`; pornit din `lifespan`, anulat la oprire.",
      "În `routers/events.py`: scoate tick-ul fals din generator; la 15 s fără evenimente trimite comentariul `: ping\\n\\n`.",
      "`deps.publish`: `at` = `clock.now()`.",
      "Verifică toate serviciile scrise până acum: publică **după** commit (`publish_all`).",
      "Test: abonează un client, publică un eveniment cu `crew_id=\"cm-1\"`; contul `specialist2` nu-l primește, `medic` da."],
     ["`app/services/mission.py`", "`app/routers/events.py`", "`app/main.py`", "`tests/routers/test_events.py` (nou)"],
     [PYTEST, SMOKE, "`curl -N -H 'Authorization: Bearer mock-specialist2' localhost:8000/api/v1/events` arată un tick pe secundă"],
     pitfalls=["Un `asyncio.Queue` pe abonat (există); nu bloca bucla cu operații lente în generator."])

# ---------------------------------------------------------------------------------------------------------- coada
task("T23", "coada-creare", "Coada: crearea pachetelor", "A", "P0", 60, ["T17"],
     "Pachetele se creează sigilate în tabelul `packets`: din escaladarea la nivelul 3, din rezumatul aprobat (`/link/outbox`) și din răspunsul Pământului (`/earth/replies`).",
     ["`backend/app/link/queue.py` (schelet)", "`backend/app/security/sealing.py`", "`backend/app/routers/link.py` (mock)", "`backend/app/db/models/link.py`", "`contract/api/README.md` §7.6 (ce conține `payload` după `kind`)"],
     ["`link/queue.enqueue`: `id = next_id(\"pk\")`, `seq = next_seq(direction)`, `header = {id, seq, direction, kind, key_id, created_at}` (`sealing.HEADER_FIELDS`), `sealed = sealing.seal(payload, header, sender=\"ship\" | \"earth\")`, `size_bytes = len(sealed)`, `status=\"queued\"`.",
      "Escaladarea la nivelul 3 (T17, `# TODO T23`): `enqueue(kind=\"alert_l3\", payload={\"alert\": <Alert ca JSON>, \"note\": …})`, `alert.packet_id`, istoric `packet_sent`. Același lucru în `pipeline` pentru nivel 3 automat.",
      "`POST /link/outbox` (weekly_summary / alert_l3), `POST /earth/replies` (`direction=\"up\"`, `kind=\"earth_reply\"`, `payload={\"body\", \"alert_id\"}`).",
      "`GET /link/packets` (filtre, cele mai noi primele; `progress` și `eta_real_s` calculate la răspuns), `GET /link/packets/{id}` (`payload` doar dacă `delivered` și rolul are voie, altfel `null`; `crypto` din antet).",
      "Teste: escaladarea la 3 creează un pachet `queued` cu `seq` 1; al doilea are `seq` 2; `earth` nu vede `payload` până la livrare."],
     ["`app/link/queue.py`", "`app/services/link.py`", "`app/services/alerts.py`", "`app/services/pipeline.py`", "`app/routers/link.py`", "`tests/link/test_enqueue.py` (nou)"],
     [PYTEST, SMOKE],
     dont=["Nu salva conținutul în clar la creare: doar `sealed`. `payload` se completează la livrare (T24)."])

task("T24", "coada-planificator", "Coada: planificatorul", "A", "P0", 60, ["T23"],
     "Un task din fundal trimite pachetele când fereastra e deschisă, le livrează după întârzierea mediului, le deschide (`sealing.open`) și le marchează livrate sau respinse.",
     ["`backend/app/link/scheduler.py`, `link/windows.py` (schelet)", "`backend/app/security/sealing.py`, `security/errors.py`", "`backend/app/services/events.py`", "`contract/api/README.md` §7.6"],
     ["`windows.one_way_delay_s` din `data/environments.json` pentru mediul curent; `window_open` = `True` (prototip).",
      "`link_scheduler`: buclă la 1 s, cu sesiune proprie: `queued` → `in_transit` (`sent_at`, `arrives_at = sent_at + delay`) → `packet.sent`; `in_transit` cu `arrives_at <= clock.now()` → `sealing.open` → `delivered` (`payload`, `delivered_at`, `signature_valid=True`) sau `SealError` → `rejected` (`reject_reason`, `signature_valid=False`) → `packet.arrived` / `packet.rejected`.",
      "La livrarea unui `earth_reply` cu `alert_id`: `alert.earth_reply = body`, istoric `earth_replied`, `alert.updated` (cu `crew_id`).",
      "`GET /crew/{id}/messages`: pachetele `up` livrate pentru membrul acela (și `donki_alert` pentru toți).",
      "Evenimentele după commit; bucla nu se oprește la o eroare (log + continuă).",
      "Teste (cu `clock.freeze` mutat manual): pachetul ajunge după exact întârzierea mediului; un pachet cu antetul modificat după sigilare e `rejected`; răspunsul Pământului apare la astronaut după a doua întârziere."],
     ["`app/link/scheduler.py`", "`app/link/windows.py`", "`app/services/link.py`", "`app/main.py`", "`tests/link/test_scheduler.py` (nou)"],
     [PYTEST, SMOKE, "în demo, cu ×60 pe Marte (700 s), pachetul ajunge în ~11,7 s reale"],
     pitfalls=["Pachetele deja `in_transit` își păstrează `arrives_at` la schimbarea mediului."])

# ---------------------------------------------------------------------------------------------------------- radiații
task("T25", "radiatii", "Radiații: generator, detector, adăpost", "B", "P1", 60, ["T16"],
     "Dozimetrul simulat dă rata dozei; la furtună rata urcă, detectorul dă alerta de nivel 1 după 3 citiri peste 2 × media pe 24 h, iar „Sunt în adăpost” aplică ecranarea.",
     ["`backend/app/simulator/radiation.py`, `engine/radiation.py`, `simulator/live.py` (schelet)", "`backend/app/routers/radiation.py`, `routers/demo.py` (sep/start, sep/stop)", "`data/parameters.json`: `prag_alerta_sep_rata_vs_baseline`, `reducere_doza_adapost_capsula`", "`data/donki/donki_sep_event.json`", "`engine/derived.py` (SEP_CONSECUTIVE_READINGS)"],
     ["`simulator/radiation.dose_rate`: fond din mediu (`baseline_dose_usv_h`) + zgomot ±5%; după onset: urcă în ~20 min la `peak_multiplier` (6) × fond, scade exponențial în ore; × `shield_factor` (0,3) în adăpost.",
      "`engine/radiation`: `mean_24h`, `is_alert` (ultimele 3 ≥ 2 × medie).",
      "`POST /sim/sep/start`: `sim_state[\"storm\"] = {event_id, onset_at = acum + starts_in_min}`; `stop`: șterge starea → `radiation.cleared`.",
      "`live_simulator` (pas 2 s, din `lifespan`): cât e furtună, o citire nouă (`RadiationReading`) la fiecare pas; la alertă → `Finding(radiation, level 1, \"radiation-1-1\")` prin pipeline, `onboard_alert_at`, `radiation.alert`; `radiation.reading` cel mult la 2 s.",
      "`POST /radiation/shelter-ack`: `sheltered_since`; `GET /radiation/status` (cu `profile_is_synthetic=True`), `GET /radiation/series`.",
      "Teste (ceas mutat manual): 2 citiri peste prag → fără alertă; a 3-a → alertă; în adăpost rata scade."],
     ["`app/simulator/radiation.py`", "`app/engine/radiation.py`", "`app/simulator/live.py`", "`app/services/radiation.py`", "`app/routers/radiation.py`", "`app/routers/demo.py`", "`tests/engine/test_radiation.py` (nou)"],
     [PYTEST, SMOKE, "`test_sep_alert_at_2x_mean` există"],
     dont=["Nu inventa doza măsurată pentru evenimentul din 2024: nu e publicată; curba e sintetică și marcată așa."])

task("T26", "furtuna-donki", "Furtuna: avertizarea DONKI prin coadă", "B", "P1", 40, ["T24", "T25"],
     "Avertizarea Pământului vine ca pachet `donki_alert` pe direcția `up`, cu întârzierea legăturii; la sosire se calculează cu câte minute a fost SHADOW mai rapid (`lead_minutes`).",
     ["`backend/app/link/queue.py`", "`backend/app/services/radiation.py`", "`data/donki/donki_sep_event.json`", "`contract/api/README.md` §7.7"],
     ["La `sep/start`: programează avertizarea Pământului la ora alertei NASA din fișier, relativ la onset (alerta `20240511-AL-006` a venit la 20 min după onset).",
      "Când vine momentul (în `live_simulator`): `enqueue(direction=\"up\", kind=\"donki_alert\", payload={\"event\": SepEvent, \"issued_at\": …})`.",
      "La livrare (în planificator): `earth_warning_arrived_at`; `lead_minutes = (earth_warning_arrived_at − onboard_alert_at)` în minute de misiune.",
      "Dacă doza din eveniment trece `prag_doza_eveniment_nivel3` (10% din 250 mGy-Eq) → alertă de nivel 3 → pachet `alert_l3`.",
      "Test: cu ceasul mutat, `lead_minutes` e pozitiv și egal cu întârzierea + decalajul alertei NASA."],
     ["`app/services/radiation.py`", "`app/simulator/live.py`", "`app/link/scheduler.py`", "`tests/link/test_donki_uplink.py` (nou)"],
     [PYTEST, SMOKE])

# ---------------------------------------------------------------------------------------------------------- ceilalți piloni
task("T27", "inima", "Pilonul Inima", "B", "P1", 45, ["T16"],
     "Scorul de pregătire pentru revenire (0–100) din pulsul de repaus, HRV și tensiune, față de baseline-ul din zbor. Praguri derivate, prezentate ca ipoteză.",
     ["`backend/app/engine/pillars/cardio.py` (schelet)", "`data/parameters.json`: `prag_hr_repaus_crestere`, `prag_hrv_lnrmssd`, `prag_tas_scadere_in_zbor`", "`data/catalog/recommendations.json` (cardio-*)"],
     ["Puls de repaus: media pe 7 zile > baseline + 1 × CV personal, ≥ 3 zile → `watch`.",
      "HRV (lnRMSSD): media pe 7 zile < baseline − 0,5 × CV → `watch`.",
      "Ambele, sau unul + simptome la check-in → `Finding(cardio, level 2)`.",
      "Scorul: 100 − penalizări; scris în `measurements` ca `landing_readiness` pe zi (pentru grafic și derulator).",
      "Înlocuiește valorile mock din panoul Inima (T21).",
      "Teste: zilele 110–118 nu există încă (misiunea e în ziua 96) → testează pe serii scrise de mână; pe scenariu, scorul lui cm-2 e ≥ 80 în ziua 96."],
     ["`app/engine/pillars/cardio.py`", "`app/services/crew.py`", "`tests/engine/test_cardio.py` (nou)"],
     [PYTEST, SMOKE],
     dont=["Nu compara cu valorile de pe Pământ: în zbor tensiunea scade normal și pulsul nu crește."])

task("T28", "incarcarea", "Pilonul Încărcarea + exerciții", "B", "P1", 45, ["T16"],
     "Scorul de încărcare osoasă pe sesiune și pe zi, recomandarea de a împărți antrenamentul, seria de zile și proiecția (estimare) a pierderii osoase.",
     ["`backend/app/engine/pillars/musculoskeletal.py` (schelet)", "`backend/app/routers/exercise.py` (mock)", "`data/parameters.json`: `projected_bmd_loss_model`, `alert_strength_drop_level2`, `alert_strength_drop_level3`"],
     ["`session_score`: Σ repetări × greutate, cu randament descrescător după primele 5 repetări ale fiecărui set; normalizat ca o zi normală să fie ~80.",
      "`daily_loading`: suma; bonus 20% dacă sunt două sesiuni la ≥ 4 ore distanță.",
      "`split_recommended`: o singură sesiune făcută/planificată azi.",
      "Seria `split_training`: zile consecutive cu antrenament împărțit.",
      "`projection`: din ratele lunare din `projected_bmd_loss_model` × aderența; varianta împărțită puțin mai bună; `note` spune că e estimare, demonstrată doar pe animale.",
      "Endpoint-urile: `GET …/exercise/today`, `POST …/exercise/sessions` (salvează, `source=\"manual\"`, apoi `dashboard.changed`), `GET …/exercise/sessions`.",
      "Teste: a doua sesiune la 7 ore distanță crește scorul zilei cu bonusul; ziua 61 (sărită) dă `split_recommended`."],
     ["`app/engine/pillars/musculoskeletal.py`", "`app/services/exercise.py`", "`app/routers/exercise.py`", "`tests/engine/test_loading.py` (nou)"],
     [PYTEST, SMOKE])

task("T29", "semnale-incrucisate", "Semnale încrucișate + cauza de mediu", "B", "P1", 45, ["T16"],
     "Trei abateri mici din piloni diferiți la același om devin un semnal încrucișat; aceeași abatere la cel puțin 3 din 4 membri în aceeași zi înseamnă cauză de mediu (cabina), nu individuală.",
     ["`backend/app/engine/cross_signals.py` (schelet)", "`engine/derived.py` (ENVIRONMENTAL_MIN_CREW, CROSS_SIGNAL_WINDOW_DAYS)", "`data/scenario/scenario.json` (zilele 40–41: somn prost la toți)"],
     ["`environmental_cause`: grupează constatările zilei pe subiect; ≥ 3 membri → subiectul are cauză de mediu.",
      "În `pipeline`: rulează pentru toți membrii în aceeași zi (în replay e natural; live, după fiecare zi nouă); setează `cause=\"environmental\"` și `cause_explanation` („Aceeași abatere la 4 din 4 membri: problema e probabil în cabină.”).",
      "`detect`: semnalele din ultimele 3 zile la același om, din ≥ 2 piloni → `CrossSignal` cu `confidence` și explicație; apare în `dashboard.cross_signals`.",
      "Teste: în ziua 40 alertele de somn/tastare au `cause=\"environmental\"`; alerta imunitară a lui cm-2 are `individual`; cm-2 în ziua 96 are un semnal încrucișat (imunitar + comportamental)."],
     ["`app/engine/cross_signals.py`", "`app/services/pipeline.py`", "`app/services/crew.py`", "`tests/engine/test_cross_signals.py` (nou)"],
     [PYTEST, SMOKE])

task("T30", "reverificare", "Reverificarea alertelor", "B", "P2", 30, ["T17"],
     "La `recheck_at`, SHADOW verifică dacă planul a funcționat: valorile au revenit → alerta se închide singură; nu → urcă un nivel.",
     ["`backend/app/services/alerts.py` (recheck_loop)", "`backend/app/services/pipeline.py`"],
     ["Buclă la 5 s (din `lifespan`): alertele deschise cu `recheck_at <= clock.now()`.",
      "Rulează regula pilonului pe ziua curentă: fără constatare → `resolved`, istoric `rechecked` + `resolved` („valorile au revenit”); cu constatare → `level + 1` (max 3), `recheck_at` nou, istoric `rechecked`.",
      "Evenimente după commit: `alert.updated`.",
      "Test: o alertă cu `recheck_at` trecut și valori normale se închide; una cu valori încă mari urcă la nivelul următor."],
     ["`app/services/alerts.py`", "`app/main.py`", "`tests/routers/test_recheck.py` (nou)"],
     [PYTEST, SMOKE])

# ---------------------------------------------------------------------------------------------------------- AI, securitate, demo
task("T31", "puntea-ai", "Puntea către medicul AI", "A", "P1", 45, ["T17"],
     "`POST /ai/chat` construiește contextul (alerta, dovezile, recomandarea din catalog), apelează serviciul AI cu limită de 20 s și cade pe textul din catalog dacă nu răspunde. Niciodată eroare din cauza AI-ului.",
     ["`backend/app/routers/ai.py` (mock)", "`backend/app/services/ai.py` (schelet)", "`backend/app/ai_schemas.py`", "`contract/ai/README.md` §3–5"],
     ["Astronautul întreabă doar despre `crew_id`-ul lui (regula există).",
      "Contextul `AiContext`: din `alert_id` (dacă e dat): topic, level, titlu, dovezi, recomandarea din catalog; plus `mission_day`, mediul. **Fără nume și fără `crew_id`.**",
      "Apel: `httpx.AsyncClient(timeout=settings.ai_timeout_s).post(f\"{settings.ai_url}/chat\", json=…)`, **fără sesiune de bază deschisă** în timpul așteptării.",
      "Răspuns → `AiChatResponse` (`fallback=False`, `latency_ms` măsurat, `disclaimer`).",
      "Orice eroare (timeout, conexiune refuzată, 503, 422) → `answer = recommendation.action`, `citations = [sursa recomandării]`, `fallback=True`, `model=\"catalog\"`.",
      "`GET /ai/status`: din `GET {ai_url}/status`; dacă nu răspunde → `ready=False`, `mode=\"fallback\"`.",
      "Teste: cu serviciul AI oprit, `/ai/chat` dă 200 și `fallback=True`; cu mock-ul AI pornit (sau `httpx.MockTransport`), `fallback=False` și citarea vine din serviciu."],
     ["`app/services/ai.py`", "`app/routers/ai.py`", "`tests/routers/test_ai_bridge.py` (nou)"],
     [PYTEST, SMOKE, "`cd ai && uv run uvicorn service.main:app --port 8001` + backend → răspunsul vine din mock-ul AI"])

task("T32", "dispozitive-dovezi", "Măsurători de la dispozitive, respingeri, dovezi", "A", "P1", 60, ["T08", "T16"],
     "`/ingest/measurements` verifică semnătura și plauzibilitatea, salvează sau respinge; `/security/rejections`, `/evidence/tests` și `/evidence/parameters` lucrează cu date reale.",
     ["`backend/app/routers/security.py` (mock)", "`backend/app/services/security_log.py` (schelet)", "`backend/app/security/signing.py`, `security/validation.py`", "`backend/app/simulator/devices.py` (schelet)"],
     ["`ingest`: `signing.verify(obj, signature_b64, keys.device_public.get(device_id))` → altfel `Rejection(kind=\"bad_signature\")`; apoi `validation.check(metric_key, value, repos.recent_device_values(...), limite din checkin_indicators)` → `implausible` / `frozen_sensor`; altfel `Measurement(source=\"device\")` + `pipeline.process`.",
      "Respingerea: `Rejection` cu `next_id(\"rj\")`, `measurement.rejected` după commit; răspunsul e tot 200 cu `accepted=False`.",
      "`simulator/devices.signed_measurement`: forma `MeasurementIngest`, semnată peste `signing.canonical()`.",
      "`GET /security/rejections` din bază, cele mai noi primele.",
      "`GET /evidence/tests`: rulează o dată la pornire `pytest tests/engine -q --json-report`-like (sau `pytest --junitxml` într-un fișier temporar, prin `asyncio.create_subprocess_exec`) și ține rezultatul; endpoint-ul îl întoarce.",
      "`GET /evidence/parameters`: din `data.params` (mock-ul face deja asta; mută-l în serviciu).",
      "Teste: o măsurătoare modificată după semnare → respinsă; 20 de valori identice → `frozen_sensor`; puls 400 → `implausible`."],
     ["`app/services/security_log.py`", "`app/simulator/devices.py`", "`app/routers/security.py`", "`tests/security/test_ingest.py` (nou)"],
     [PYTEST, SMOKE],
     pitfalls=["Până la varianta reală a securității, `signing.verify` acceptă orice semnătură nevidă în afară de `\"invalid\"`: testele de respingere folosesc `\"invalid\"`."])

task("T33", "demo", "Demo: reset, salt de zi, atacuri", "A", "P0", 60, ["T24"],
     "Butoanele de demo merg pe date reale: `/sim/reset` reface totul (ziua 96) în câteva secunde, `PUT /sim/clock` sare înainte, pachetul falsificat e respins de coadă, senzorul înghețat e respins de validare.",
     ["`backend/app/routers/demo.py`, `routers/mission.py` (sim/clock)", "`backend/app/services/demo.py` (schelet)", "`backend/app/main.py` (lifespan)", "`security/attacks/` (scripturile echipei de securitate)"],
     ["Extrage din `lifespan` o funcție `bootstrap(app)` (bază + seed + istoric + replay + ceas) și una `start_tasks / stop_tasks`.",
      "`/sim/reset`: `stop_tasks` → golește tabelele (sau `drop_all` + `create_all`) → `bootstrap` → `start_tasks` → `lockout.reset_all()` → `dashboard.changed` (`reason=\"reset\"`) și `mission.tick`. Țintă: sub 5 s.",
      "`PUT /sim/clock` cu `mission_day` (înainte): generează zilele lipsă cu `scenario.generate(from_day=curent+1, to_day=nou)`, scrie-le, rulează `pipeline` pe ele, apoi `clock.jump_to_day`; `dashboard.changed` (`reason=\"jump\"`).",
      "`/demo/inject-spoof`: creează un pachet `down` sigilat cu `sender=\"attacker\"` (varianta provizorie a `sealing` îl respinge; cea reală, prin cheia greșită) → planificatorul îl respinge → `packet.rejected`.",
      "`/demo/frozen-sensor`: trimite prin `ingest` de 20 de ori aceeași valoare → a 20-a e respinsă.",
      "Teste: după reset, ziua e 96 și alertele sunt cele din replay; saltul la ziua 98 creează zilele 97–98; pachetul falsificat ajunge `rejected`."],
     ["`app/services/demo.py`", "`app/routers/demo.py`", "`app/routers/mission.py`", "`app/main.py`", "`tests/routers/test_demo.py` (nou)"],
     [PYTEST, SMOKE, "repetiția completă a demo-ului de două ori la rând, cu `/sim/reset` între ele"])

task("T34", "scoaterea-mockului", "Scoaterea mock-ului și verificarea finală", "A+B", "P0", 45, ["toate"],
     "Niciun router nu mai folosește `app/examples.py`; fișierul se șterge; `/health` spune `mode: real`; toate verificările trec pe backend-ul real.",
     ["`backend/handoff/04_SCHELET.md` (ce a rămas „mock”)", "`scripts/smoke.py`"],
     ["`grep -rn \"examples\" app/` → fiecare utilizare rămasă se înlocuiește cu serviciul ei.",
      "Șterge `app/examples.py`; `/health` → `\"mode\": \"real\"`.",
      "`ALLOW_MOCK_TOKENS`: rămâne `true` doar dacă frontend-ul încă folosește tokenuri mock; altfel `false` în `.env` de demo (smoke.py folosește mock — rulează-l cu `ALLOW_MOCK_TOKENS=true`).",
      "Regenerează documentele: `scripts/build_docs.py`, `scripts/build_handoff.py`, `scripts/gen_types.sh`.",
      "Repetă demo-ul complet cu frontend-ul pornit.",
      "Lista finală: niciun `NotImplementedError` rămas pe drumul demo-ului (`grep -rn NotImplementedError app/`)."],
     ["toate"],
     [PYTEST, SMOKE, "`grep -rn \"examples\\|NotImplementedError\" app/` nu găsește nimic pe drumul demo-ului", "demo-ul merge cap-coadă de două ori la rând"])


# ---------------------------------------------------------------------------------------------------------- randare
def render(t, by_id):
    deps = ", ".join(t["depends"]) if t["depends"] else "—"
    unblocks = ", ".join(x["id"] for x in T if t["id"] in x["depends"]) or "—"
    out = [f"# {t['id']} — {t['title']}", "",
           f"**Cine:** {t['who']} · **Prioritate:** {t['prio']} · **Durată estimată:** ~{t['minutes']} min · "
           f"**Depinde de:** {deps} · **Deblochează:** {unblocks}", "",
           "## Ce construiești", "", t["goal"], "",
           "## De citit (atașează-le lui Claude)", "",
           "- `backend/handoff/01_CONTEXT.md` (mereu)"]
    out += [f"- {r}" for r in t["read"]]
    out += ["", "## Pași", ""]
    out += [f"{i}. {s}" for i, s in enumerate(t["steps"], 1)]
    out += ["", "## Fișierele atinse", ""]
    out += [f"- {f}" for f in t["files"]]
    out += ["", "## Gata când", ""]
    out += [f"- [ ] {d}" for d in t["done"]]
    out += ["- [ ] `uv run ruff check app tests` → fără erori", "- [ ] PR mic, titlul `backend: " + t["id"] + " " + t["title"].lower() + "`"]
    if t["dont"]:
        out += ["", "## Nu face", ""] + [f"- {d}" for d in t["dont"]]
    if t["pitfalls"]:
        out += ["", "## Capcane", ""] + [f"- {p}" for p in t["pitfalls"]]
    out += ["", "## Regula generală", "",
            "Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,",
            "`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional",
            "pentru tot ce nu ține de acest task."]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    outdir = pathlib.Path(sys.argv[1])
    outdir.mkdir(parents=True, exist_ok=True)
    for f in outdir.glob("T*.md"):
        f.unlink()
    by_id = {t["id"]: t for t in T}
    for t in T:
        (outdir / f"{t['id']}-{t['slug']}.md").write_text(render(t, by_id), encoding="utf-8")
    # verificări
    ids = [t["id"] for t in T]
    assert ids == [f"T{i:02d}" for i in range(len(T))], ids
    for t in T:
        for d in t["depends"]:
            assert d == "toate" or d in by_id, (t["id"], d)
    print(f"{len(T)} taskuri scrise în {outdir}")
