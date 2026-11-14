# SHADOW — planul de atac pentru backend

**Pentru:** echipa de backend (2 oameni) + echipa de securitate (scrie în `backend/app/security/`)
**Stack:** Python 3.12 · uv · FastAPI · Pydantic v2 · SQLAlchemy 2.0 **asincron** · SQLite (aiosqlite) · pytest

Documentul spune **cum** construim backend-ul: deciziile, arhitectura, regulile de cod și ordinea pe ore.
**Ce** trebuie construit (fiecare funcționalitate, cu regulile și criteriul „gata când”) e în `BACKEND_SARCINI.md`.
**Contractul** (endpoint-uri, modele, erori, evenimente) e în `contract/README.md`. Când cele trei se contrazic,
contractul câștigă, apoi acest plan.

## Cuprins

1. [Deciziile](#1-deciziile)
2. [Pornirea, prima oră](#2-pornirea-prima-oră)
3. [Arhitectura](#3-arhitectura)
4. [Regulile pentru cod asincron](#4-regulile-pentru-cod-asincron)
5. [Baza de date](#5-baza-de-date)
6. [Pornirea aplicației](#6-pornirea-aplicației)
7. [Ceasul misiunii](#7-ceasul-misiunii)
8. [Drumul unei date](#8-drumul-unei-date)
9. [Motorul](#9-motorul)
10. [Task-urile din fundal](#10-task-urile-din-fundal)
11. [Evenimentele live](#11-evenimentele-live)
12. [Granița cu securitatea](#12-granița-cu-securitatea)
13. [Testele](#13-testele)
14. [Git](#14-git)
15. [Planul pe ore](#15-planul-pe-ore)
16. [Convenții de cod](#16-convenții-de-cod)
17. [Riscuri și ce tăiem](#17-riscuri-și-ce-tăiem)
18. [Comenzi](#18-comenzi)

---

## 1. Deciziile

| Subiect | Decizie | De ce |
|---|---|---|
| Limbaj și pachete | Python 3.12, **uv** | lock comun (`uv.lock`), instalare rapidă, aceleași versiuni la toți |
| API | FastAPI | contractul e deja scris în FastAPI; scheletul rulează |
| Validare | Pydantic v2 | modelele din `app/schemas.py` sunt contractul |
| Setări | `pydantic-settings` | citește `.env`, validează tipurile la pornire |
| ORM | SQLAlchemy 2.0, **asincron** (`AsyncSession`) | ales de echipă; tot backend-ul e `async def` |
| Driver | `aiosqlite` | driverul asincron pentru SQLite |
| Baza de date | un fișier SQLite, mod WAL | fără server; WAL permite citiri în timp ce se scrie |
| Migrări | **fără**: `create_all()` + seed la fiecare pornire | toate datele sunt generate (seed + scenariu); nu avem nimic de păstrat între rulări; zero timp pierdut pe migrări |
| Timpul în demo | **pornim din ziua 96**: zilele 1–96 se generează la pornire, apoi ceasul merge live (×60) | demo previzibil; derulatorul arată trecutul |
| Teste | pytest + `pytest-asyncio` + `httpx.AsyncClient` | aceleași unelte pentru motor și pentru endpoint-uri |
| Stil | `ruff` (format + lint) | o singură unealtă, rapidă |
| Git | ramuri scurte + PR mic, aprobat repede | secțiunea 14 |

**Fără migrări înseamnă:** schimbi un model → oprești serverul → la pornire baza se șterge și se recreează. Nu
există comandă de migrare și nu există fișier de bază de date comis în git.

---

## 2. Pornirea, prima oră

Ordinea exactă. Unul singur (Backend A) face pașii 1–4 și îi împinge pe `main`; celălalt începe între timp cu
`parameters.json` (secțiunea 15).

Scheletul vine deja cu `pyproject.toml` (toate dependențele de mai jos), `uv.lock` și `.python-version`:

```bash
# 1. dependențele
cd backend
uv sync

# 2. mock-ul pornește
uv run uvicorn app.main:app --reload --port 8000

# 3. testele de bază și verificarea contractelor trec
uv run pytest
cd .. && uv run --project backend python scripts/smoke.py
```

Dependențele, pentru referință (deja în `pyproject.toml`): `fastapi`, `uvicorn[standard]`, `pydantic`,
`pydantic-settings`, `sqlalchemy[asyncio]`, `aiosqlite`, `httpx`, `pyyaml`; pentru dezvoltare `pytest`,
`pytest-asyncio`, `asgi-lifespan`, `ruff`. Una nouă: `uv add <pachet>`, într-un PR separat.

Configurația din `backend/pyproject.toml` (deja acolo):

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
pythonpath = ["."]          # fără el, pytest nu găsește pachetul `app` (proiectul uv e „bare”)

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "ASYNC"]
ignore = [
  "B008",      # Depends(...) în argumente: tiparul normal din FastAPI
  "ASYNC110",  # buclele din fundal cu asyncio.sleep sunt intenționate (secțiunea 10)
  "E501",      # rânduri lungi: descrierile din contract sunt text
  "UP042",     # (str, Enum) în loc de StrEnum: forma pe care o citește corect OpenAPI
]

[tool.ruff.lint.per-file-ignores]
"app/examples.py" = ["F403", "F405"]   # mock-ul importă toate modelele; dispare pe parcurs
```

Regula `ASYNC` din ruff prinde apeluri blocante în funcții `async def` (de exemplu `time.sleep`). Configurația
de mai sus e verificată: testele trec, iar ruff nu semnalează tiparele pe care le folosim intenționat.

---

## 3. Arhitectura

### Straturile

```
  HTTP (frontend, simulator, scripturi de atac)
        │
┌───────▼────────────────────────────────────────────────────────┐
│ routers/      citesc cererea, verifică rolul, apelează un       │
│               serviciu, întorc un model din schemas.py          │
├────────────────────────────────────────────────────────────────┤
│ services/     logica aplicației: tranzacții, ordinea pașilor,   │
│               scrieri în bază, publicarea evenimentelor         │
├──────────────────────────┬─────────────────────────────────────┤
│ engine/                  │ db/                                  │
│ funcții PURE: primesc    │ modelele SQLAlchemy, sesiunea,       │
│ date, întorc rezultate;  │ interogările refolosite (repos)      │
│ fără bază, fără HTTP,    │                                      │
│ fără ceas                │                                      │
├──────────────────────────┴─────────────────────────────────────┤
│ security/  (echipa de securitate)   clock.py   config.py        │
└────────────────────────────────────────────────────────────────┘
        ▲
 simulator/  și  link/scheduler.py  (task-uri din fundal; folosesc services/)
```

### Regula de dependență

| Stratul | Poate importa | NU poate importa |
|---|---|---|
| `routers/` | `services/`, `schemas`, `deps` | `db/models` direct (doar prin servicii), `engine/` |
| `services/` | `engine/`, `db/`, `security/`, `clock`, `deps.publish` | `routers/` |
| `engine/` | doar biblioteca standard și propriile modele de date | `db/`, `fastapi`, `clock`, `security/` |
| `db/` | `sqlalchemy`, `config` | orice altceva din aplicație |
| `simulator/`, `link/` | `services/`, `db/`, `clock`, `security/` | `routers/` |

De ce contează: `engine/` fiind pur, îl testezi fără bază de date, în milisecunde, iar regulile medicale (praguri,
niveluri) stau într-un singur loc. Routerele rămân subțiri: dacă un router are mai mult de 15 rânduri, logica
lui trebuie mutată într-un serviciu.

### Scheletul, cu ce se adaugă față de `STRUCTURA_REPO.md`

Două schimbări, ca să evităm conflictele pe git: modelele bazei de date sunt împărțite pe domenii (un singur
`models.py` ar fi editat de toți în același timp), iar logica din routere se mută în `services/`.

```
backend/app/
├── main.py                 aplicația + lifespan (secțiunea 6)
├── config.py               setările (pydantic-settings)
├── clock.py                SimClock
├── ids.py                  generatorul de id-uri cu prefix (al-0001, pk-0001…)
├── schemas.py              contractul API (nu se schimbă fără anunț)
├── ai_schemas.py           EXISTĂ: contractul cu serviciul AI (copie a ai/service/schemas.py)
├── datafiles.py            EXISTĂ: formatul fișierelor din data/ + load_all()
├── deps.py                 current_user, require_roles, crew_access, get_session, publish
├── examples.py             mock-ul; se golește pe măsură ce apare logica reală
├── routers/                (există; se schimbă doar corpul funcțiilor)
├── services/               NOU
│   ├── auth.py  mission.py  crew.py  checkins.py  behavioral.py  exercise.py
│   ├── alerts.py  link.py  radiation.py  ai.py  security_log.py  demo.py
│   └── pipeline.py         „a sosit o dată nouă” → motor → alerte → evenimente
├── db/
│   ├── session.py          motorul asincron, sesiunea, pragmele SQLite
│   ├── base.py             Base, UTCDateTime, coloanele comune
│   ├── models/             NOU: câte un fișier pe domeniu
│   │   ├── users.py        users, crew, revoked_tokens
│   │   ├── measurements.py measurements, checkins, keystroke_sessions, pvt_results, exercise_sessions, radiation_readings
│   │   ├── alerts.py       alerts, plan_steps, alert_history
│   │   ├── link.py         packets
│   │   └── security.py     access_log, rejections
│   ├── repos.py            interogări refolosite (ultimele N nopți, seria unei metrici…)
│   └── seed.py             conturi + scenariu + istoric
├── engine/                 (ca în BACKEND_SARCINI.md)
├── simulator/
├── link/
└── security/               EXISTĂ: al echipei de securitate (semnături finale, corp provizoriu)
```

---

## 4. Regulile pentru cod asincron

Asincronul cu SQLite are câteva capcane. Toate regulile de mai jos au motive concrete; le-am verificat.

1. **Orice funcție care atinge baza de date e `async def`** și folosește `await session.execute(...)`.
2. **O sesiune pe cerere**, prin dependența `get_session`. Nu se ține o sesiune globală.
3. **Fără încărcare leneșă (lazy loading).** Toate relațiile au `lazy="raise"`. Dacă ai nevoie de pașii unei
   alerte, îi ceri explicit: `select(Alert).options(selectinload(Alert.steps))`. Altfel, în asincron, accesul la
   `alert.steps` aruncă `MissingGreenlet` într-un loc greu de înțeles; cu `lazy="raise"` primești o eroare clară
   chiar în linia greșită.
4. **`expire_on_commit=False`** pe sesiune, ca obiectele să poată fi citite după `commit()` fără o nouă interogare.
5. **Task-urile din fundal își deschid propria sesiune** (`async with db.SessionLocal() as s:`). O sesiune nu se
   împarte niciodată între două task-uri sau între o cerere și un task.
6. **Nimic blocant în `async def`.** Fără `time.sleep`, fără `requests`, fără citiri mari de fișiere. Pentru
   lucrul greu pe procesor folosești `await asyncio.to_thread(funcție, ...)`:
   - hash-ul parolelor (argon2 durează intenționat zeci de milisecunde);
   - generarea istoricului de 96 de zile la pornire;
   - rularea motorului peste tot istoricul.
7. **Tranzacții scurte.** SQLite are un singur scriitor la un moment dat. Nu ține o tranzacție deschisă cât aștepți
   altceva (un apel HTTP către AI, un `sleep`). Citești, închizi, apelezi, apoi scrii în altă tranzacție.
8. **Evenimentele se publică după `commit()`**, niciodată înainte (secțiunea 11).
9. **Apelul către serviciul AI** se face cu `httpx.AsyncClient`, cu limită de 20 de secunde, **fără** sesiune de
   bază de date deschisă în timpul așteptării.
10. **Datele-oră sunt mereu cu fus orar (UTC).** SQLite nu păstrează fusul orar, deci folosim tipul `UTCDateTime`
    (secțiunea 5), care refuză o dată fără fus orar la scriere și pune UTC la citire.

---

## 5. Baza de date

### Configurarea (verificată)

`app/db/session.py`. Motorul **nu** se creează la importul modulului, ci în `init_engine()`, apelată din
`lifespan`. Altfel adresa bazei de date e fixată înainte ca testele să o poată schimba.

```python
from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

engine: AsyncEngine | None = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None


def init_engine(url: str) -> AsyncEngine:
    """Apelată o singură dată, din lifespan. url = "sqlite+aiosqlite:///./shadow.sqlite"."""
    global engine, SessionLocal
    engine = create_async_engine(url)

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record) -> None:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")    # citiri în paralel cu o scriere
        cur.execute("PRAGMA foreign_keys=ON")     # SQLite le ignoră implicit
        cur.execute("PRAGMA busy_timeout=5000")   # așteaptă 5 s în loc să dea „database is locked”
        cur.close()

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    return engine


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
```

**Atenție la import:** `SessionLocal` se schimbă la pornire, deci în restul codului se importă **modulul**, nu
numele: `from app.db import session as db`, apoi `async with db.SessionLocal() as s:`. Cu
`from app.db.session import SessionLocal` ai primi valoarea `None` de dinainte de pornire.

`app/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite+aiosqlite:///./shadow.sqlite"
    reset_db_on_start: bool = True
    time_scale: float = 60
    data_dir: str = "../data"
    jwt_secret: str                       # obligatoriu: fără el, pornirea se oprește
    link_aes_key_b64: str = ""
    ai_url: str = "http://localhost:8001"
    cors_origins: list[str] = ["http://localhost:3000"]


def get_settings() -> Settings:
    return Settings()                     # se citește la apel, nu la import (pentru teste)
```

`app/db/base.py`:

```python
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """Dată-oră mereu în UTC. SQLite nu păstrează fusul orar; acest tip îl impune."""
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Dată-oră fără fus orar. Folosiți clock.now() sau datetime(..., tzinfo=UTC).")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=UTC) if value is not None else None


class Base(AsyncAttrs, DeclarativeBase):
    pass
```

### Tabelele

Toate datele-oră sunt **timp de misiune** (din `SimClock`), de tip `UTCDateTime`. Fiecare tabel cu date ale unui
astronaut are `crew_id` și `mission_day`, indexate împreună: aproape fiecare interogare filtrează după ele.

| Tabel | Coloane principale | Observații |
|---|---|---|
| `crew` | `id` (`cm-1`…), `display_name`, `initials`, `role_title`, `is_cmo` | 4 rânduri, din seed |
| `users` | `id`, `username` (unic), `password_hash`, `display_name`, `initials`, `role`, `crew_id` → `crew` | un cont pe astronaut + `earth` |
| `revoked_tokens` | `jti`, `expires_at` | pentru `logout` |
| `measurements` | `id`, `crew_id`, `metric_key`, `value`, `unit`, `measured_at`, `mission_day`, `source`, `device_id` | **tabel lung**: o valoare pe rând; aici intră pulsul de noapte, HRV, temperatura de la senzor, scorurile derivate pe zi |
| `checkins` | `id`, `crew_id`, `mission_day`, `created_at`, `mood`, câte o coloană pe indicator, `note` | **unic pe (`crew_id`, `mission_day`)** |
| `keystroke_sessions` | `session_id`, `crew_id`, `context`, `started_at`, trăsăturile agregate, `n_keys`, `is_baseline` | **fără caractere**; se actualizează la fiecare lot |
| `pvt_results` | `id`, `crew_id`, `at`, `mean_rt_ms`, `mean_speed`, `lapses`, `false_starts`, `is_practice` | |
| `exercise_sessions` | `id`, `crew_id`, `mission_day`, `kind`, `started_at`, `duration_min`, `sets` (JSON), `loading_score`, `source` | |
| `radiation_readings` | `id`, `t`, `dose_rate_usv_h`, `mean_24h_usv_h`, `sheltered` | o serie pentru toată nava |
| `alerts` | `id` (`al-…`), `crew_id`, `topic`, `level`, `status`, `state`, `title`, `explanation`, `cause`, `cause_explanation`, `evidence` (JSON), `recommendation_id`, `recheck_at`, `packet_id`, `earth_reply`, `created_at` | o alertă deschisă pe (`crew_id`, `topic`) |
| `plan_steps` | `id` (`st-…`), `alert_id` → `alerts`, `text`, `done`, `done_at`, `position` | |
| `alert_history` | `id`, `alert_id`, `at`, `actor`, `role`, `action`, `note` | |
| `packets` | `id` (`pk-…`), `seq`, `direction`, `kind`, `status`, `title`, `sender`, `level`, `alert_status`, `crew_id`, `alert_id`, `in_reply_to`, `header` (JSON), `sealed` (BLOB), `created_at`, `sent_at`, `arrives_at`, `delivered_at`, `signature_valid`, `reject_reason` | **unic pe (`direction`, `seq`)**; conținutul doar sigilat |
| `access_log` | `id` (întreg, crescător), `at`, `actor`, `actor_role`, `action`, `resource`, `crew_id`, `outcome`, `prev_hash`, `hash` | doar `INSERT`; scris de codul securității |
| `rejections` | `id` (`rj-…`), `at`, `kind`, `source`, `crew_id`, `metric_key`, `value`, `message` | |
| `sim_state` | `key`, `value` (JSON) | starea furtunii, contoarele de id-uri, `seq` pe direcție |

**Câmpuri JSON** (`evidence`, `sets`, `header`): pentru date care se citesc mereu întregi și nu se caută după ele.
Tot ce apare într-un `WHERE` e coloană normală.

**De ce un tabel lung pentru măsurători:** baseline-ul, seriile pentru grafice și derulatorul sunt aceeași
interogare pentru orice metrică (`WHERE crew_id = ? AND metric_key = ? AND mission_day BETWEEN ? AND ?`).
Cheile de metrici sunt fixe, listate în `contract/README.md`, secțiunea 3.

### Id-urile

Contractul folosește id-uri text cu prefix (`al-1042`, `pk-0007`). Le generează `app/ids.py`, dintr-un contor pe
prefix ținut în `sim_state`, în aceeași tranzacție cu scrierea: `await next_id(session, "al")` → `"al-0001"`.
`access_log.id` și `measurements.id` sunt întregi simpli.

---

## 6. Pornirea aplicației

Aplicația se construiește în `create_app()`, iar totul se întâmplă în `lifespan`, în această ordine. Durata
țintă: **sub 10 secunde**. Tiparul (`create_app` + `init_engine` + `lifespan` + task-uri) e verificat.

```python
from app.db import session as db


def delete_sqlite_files(url: str) -> None:
    path = url.split("///", 1)[-1]
    for suffix in ("", "-wal", "-shm"):
        Path(path + suffix).unlink(missing_ok=True)


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.reset_db_on_start:                       # implicit True
            delete_sqlite_files(settings.database_url)
        engine = db.init_engine(settings.database_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        app.state.data = load_all(settings.data_dir)    # app/datafiles.py; oprește pornirea, cu lista problemelor
        app.state.keys = keys.load_keys(link_aes_key_b64=settings.link_aes_key_b64)

        async with db.SessionLocal() as s:
            await seed_users(s)                  # hash-ul parolelor prin asyncio.to_thread
            await seed_history(s, until_day=96)  # zilele 1–96, toți cei 4 membri
            await replay_engine(s, until_day=96) # alertele din istoric, ca ziua 96 să arate ca în scenariu
            await s.commit()

        clock.start(day=96, hour=7, minute=0, scale=settings.time_scale)
        tasks = [asyncio.create_task(t()) for t in (link_scheduler, mission_ticker, live_simulator, recheck_loop)]
        yield
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await engine.dispose()

    app = FastAPI(title="SHADOW API", version="1.1.0", lifespan=lifespan)
    # CORS, handler-ele de erori, OpenAPI și routerele: ca în main.py-ul actual
    return app


app = create_app()          # pentru `uvicorn app.main:app`
```

Reguli:

- **`seed_history` și `replay_engine`** generează și calculează în memorie (prin `asyncio.to_thread`) și scriu în
  bază la final, cu `session.add_all(...)`, nu rând cu rând. Volumul e mic: 4 membri × 96 de zile × ~10 metrici
  ≈ 4 000 de măsurători.
- **`replay_engine`** rulează exact același motor ca la datele live, zi după zi. Așa alerta lui cm-2 din ziua 95
  apare pentru că regula NightSignal o declanșează, nu pentru că e scrisă de mână.
- **`POST /sim/reset`** refolosește aceleași funcții: oprește task-urile, golește tabelele, refă seed-ul, repornește
  ceasul la ziua 96. Durata țintă: sub 5 secunde. Se folosește între repetiții.

---

## 7. Ceasul misiunii

`app/clock.py`. **Singura sursă de timp din aplicație.** Nicăieri în cod nu apare `datetime.now()`.

```python
class SimClock:
    def start(self, day: int, hour: int, minute: int, scale: float) -> None: ...
    def now(self) -> datetime: ...              # timpul misiunii, cu tzinfo=UTC
    def mission_day(self) -> int: ...           # 1..140
    def day_start(self, day: int) -> datetime: ...
    def set_scale(self, scale: float) -> None: ... # păstrează ora curentă, schimbă doar viteza
    def jump_to_day(self, day: int) -> None: ...   # doar pentru demo; vezi mai jos
    def real_seconds(self, mission_seconds: float) -> float: ...  # pentru câmpurile *_real_s

clock = SimClock()
```

- Ziua 1 începe la `2027-01-10T00:00:00Z` (din `data/scenario/scenario.json`).
- La ×60, o zi de misiune durează 24 de minute reale; demo-ul de 4 minute acoperă circa 4 ore de misiune.
- **`jump_to_day(N)`** cu N mai mare decât ziua curentă: generează zilele lipsă cu simulatorul și rulează motorul
  peste ele, apoi mută ceasul. Cu N mai mic: refuză (`409 invalid_state`). Derulatorul **nu** folosește ceasul,
  ci doar citește istoricul cu `?as_of_day=`.
- În teste se folosește un ceas fix: `clock.freeze(datetime(...))`.

---

## 8. Drumul unei date

Toate datele noi (check-in, lot de tastare, test de reacție, sesiune de exerciții, măsurătoare de la un
dispozitiv, citire de radiații) trec prin **același** drum, în `services/pipeline.py`:

```
router                          services/pipeline.py                         după commit
  │                                                                            
  ├─► validează cererea (Pydantic)                                             
  ├─► verifică rolul și crew_id                                                
  └─► serviciul domeniului ──► 1. salvează data                                
                               2. încarcă ce-i trebuie motorului (repos)       
                               3. rulează motorul (funcții pure)               
                               4. creează / actualizează alertele              
                               5. dacă nivel 3: creează pachetul (link.queue)  
                               6. commit ─────────────────────────────────►  publish(evenimente)
```

Semnătura:

```python
async def process(session: AsyncSession, crew_id: str, changed: set[str]) -> PipelineResult:
    """`changed` = cheile de metrici atinse (ex. {"night_pulse_bpm"}). Rulează doar regulile pilonilor afectați.
    Întoarce alertele create/actualizate și evenimentele de publicat după commit."""
```

Avantajul: regula „o alertă deschisă pe subiect”, escaladarea automată și pachetul de nivel 3 sunt scrise o
singură dată, nu în fiecare router.

---

## 9. Motorul

`app/engine/`. **Funcții pure**: primesc date simple, întorc rezultate simple. Nu știu de bază de date, de HTTP
sau de ceas (primesc data ca parametru).

Modelele de date ale motorului sunt `dataclass`-uri (sau modele Pydantic) definite în `engine/types.py`, separate
de tabele și de contract:

```python
@dataclass(frozen=True)
class Point:
    day: int
    t: datetime
    value: float

@dataclass(frozen=True)
class Baseline:
    median: float
    spread: float          # deviația standard robustă
    n: int
    ready: bool

@dataclass(frozen=True)
class Finding:              # rezultatul unei reguli
    topic: str              # "immune", "behavioral"…
    level: int              # 1..3
    status: str             # "watch" | "alert"
    title: str
    evidence: list[dict]
    recommendation_id: str
```

Funcțiile principale (detaliile regulilor sunt în `BACKEND_SARCINI.md`, secțiunile 5–11):

| Fișier | Funcție | Intră | Iese |
|---|---|---|---|
| `baseline.py` | `compute(points, min_n, exclude_days)` | serie | `Baseline` |
| `pillars/immune.py` | `night_signal(nights, baseline, params)` | nopțile recente | `Finding \| None` |
| `pillars/behavioral.py` | `keystroke_features(events)`, `fatigue_index(feat, base)`, `pvt_summary(trials, params)` | timpi | trăsături, indice |
| `pillars/cardio.py` | `landing_readiness(series, baselines, params)` | serii | scor + `Finding \| None` |
| `pillars/musculoskeletal.py` | `session_score(sets)`, `daily_loading(sessions)`, `projection(...)` | sesiuni | scoruri |
| `perception_gap.py` | `compute(mood, objective_scores)` | check-in + scoruri | `PerceptionGap` |
| `cross_signals.py` | `detect(findings_by_crew, day)` | constatările tuturor | semnale + cauză |
| `radiation.py` | `detect(readings, params)` | citiri | `Finding \| None` |
| `triage.py` | `decide(findings, open_alerts, catalog)` | constatări + alerte deschise | ce se creează / actualizează / escaladează |

Pragurile vin din `app.state.data.params` (încărcate de `datafiles.load_all()` din `data/parameters.json`;
`params.value("nightsignal_red_delta_bpm")` → 4) și se dau motorului ca parametru.
**Niciun prag scris direct în motor**, cu excepția celor marcate „derivat” în plan, care stau într-un singur
fișier, `engine/derived.py`, fiecare cu un comentariu care spune că e ales de echipă.

---

## 10. Task-urile din fundal

Pornite în `lifespan`, oprite la închidere. Fiecare e o buclă `while True` cu `await asyncio.sleep(...)`, își
deschide propria sesiune la fiecare pas și **nu se oprește niciodată la o eroare**: o prinde, o scrie în log și
continuă.

| Task | Fișier | Pas (secunde reale) | Ce face |
|---|---|---|---|
| `link_scheduler` | `link/scheduler.py` | 1 | trimite pachetele `queued` când fereastra e deschisă; livrează sau respinge pachetele sosite |
| `mission_ticker` | `services/mission.py` | 1 | publică `mission.tick` |
| `live_simulator` | `simulator/live.py` | 2 | când ceasul trece de un moment (ex. 03:00 → puls de noapte; furtună activă → citire de radiații), generează datele și le trece prin `pipeline.process` |
| `recheck_loop` | `services/alerts.py` | 5 | alertele cu `recheck_at` depășit: închide sau escaladează |

Schelet comun:

```python
async def loop(step_s: float, body: Callable[[AsyncSession], Awaitable[list[Event]]]) -> None:
    while True:
        try:
            async with db.SessionLocal() as s:
                events = await body(s)
                await s.commit()
            for e in events:
                publish(e.type, e.data, e.crew_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("task din fundal")
        await asyncio.sleep(step_s)
```

---

## 11. Evenimentele live

`publish()` din `deps.py` există și funcționează. Reguli:

1. **Doar după `commit()`.** Dacă publici înainte și tranzacția eșuează, frontend-ul reîncarcă și nu găsește ce
   i-ai anunțat. Serviciile întorc lista de evenimente; routerul sau bucla le publică după commit.
2. **Un eveniment pe schimbare, nu pe rând scris.** Un check-in care creează două alerte trimite un
   `dashboard.changed` și două `alert.created`, nu zece.
3. **`radiation.reading` cel mult o dată la 2 secunde reale**, chiar dacă simulatorul generează mai des.
4. **`crew_id` pe orice eveniment care privește un singur om**, ca filtrul pe cont să funcționeze.
5. Lista tipurilor și forma câmpului `data`: `contract/README.md`, secțiunea 6. Un tip nou se adaugă întâi în
   `schemas.SseEvent`.

---

## 12. Granița cu securitatea

Echipa de securitate scrie în `backend/app/security/`; noi doar apelăm. Numele și semnăturile se stabilesc în
**prima oră** și nu se mai schimbă (lista completă: `SECURITATE_SARCINI.md`, secțiunea 12).

Ce trebuie să știe ambele echipe, legat de asincron:

| Funcție | Sincronă sau asincronă | Cum o apelăm |
|---|---|---|
| `passwords.hash`, `passwords.verify` | sincronă, **lentă intenționat** | `await asyncio.to_thread(passwords.verify, pw, h)` |
| `tokens.issue`, `tokens.decode` | sincronă, rapidă | direct |
| `tokens.revoke`, `tokens.is_revoked` | **asincrone** (scriu/citesc în bază) | `await tokens.revoke(session, jti, expires_at)` |
| `lockout.check/record_failure/clear` | sincronă, în memorie | direct |
| `signing.sign/verify` | sincronă, rapidă | direct |
| `sealing.seal/open` | sincronă, rapidă | direct |
| `validation.check` | sincronă, primește valorile recente și limitele | direct (noi încărcăm valorile recente și limitele din `checkin_indicators.json`) |
| `access_log.write` | **asincronă** (scrie în bază) | `await access_log.write(session, ...)`, în tranzacția cererii |

Variantele provizorii **există deja** în `backend/app/security/`, cu semnăturile finale (de exemplu `seal` care
doar împachetează, `signing.verify` fără criptografie). Noi le apelăm de la început, iar securitatea le înlocuiește
cu varianta reală fără să ne atingă codul. Fiecare modul listează funcțiile neterminate în constanta `PROVIZORIU`;
`scripts/smoke.py` le numără. Până la ora 12, listele trebuie să fie goale. Referința completă:
`contract/security/README.md`. **Retrimiterea unui pachet o detectăm noi** (unic pe `direction` + `seq`), nu `sealing`.

---

## 13. Testele

### Ce testăm

| Ce | Unde | Cum |
|---|---|---|
| motorul (regulile) | `tests/engine/` | funcții pure, fără bază; rapide; **aici e grosul testelor** |
| endpoint-urile | `tests/routers/` | `httpx.AsyncClient` peste aplicație, cu bază temporară |
| coada | `tests/link/` | ceas fix, mutat manual; pachet trimis, livrat, respins |
| securitatea | `tests/security/` | scrise de echipa de securitate |
| contractul | `scripts/smoke.py` | rulat înainte de fiecare PR |

Testele minime care **trebuie** să existe până la ora 16 (apar în ecranul Evidence):

1. NightSignal: alertă roșie în a doua noapte la +4 bpm, nu în prima.
2. Decalajul de percepție: „4/5” cu date slabe dă `gap ≥ 25` și `status = alert`.
3. Cauza de mediu: aceeași abatere la 3 din 4 membri dă `cause = environmental`.
4. Furtuna: alertă la 3 citiri peste 2 × media, nu la una.
5. Coada: pachetul ajunge după întârzierea mediului; unul cu semnătură greșită e respins.
6. Conturi: fiecare cont își vede doar datele lui.

### Baza de date în teste: fișier temporar, NU în memorie

Am verificat: o bază SQLite în memorie (`sqlite+aiosqlite://` cu `StaticPool`) folosește o singură conexiune
pentru toate sesiunile, iar scrierile în paralel **se pierd fără nicio eroare** (din 50 de scrieri simultane s-au
salvat 18). Pe fișier, toate 50 au ajuns. Deci testele folosesc un fișier temporar:

`tests/conftest.py`:

```python
import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'test.sqlite'}")
    monkeypatch.setenv("TIME_SCALE", "1")
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.main import create_app                     # aplicația creată DUPĂ setarea mediului
    app = create_app()
    async with LifespanManager(app):                    # rulează lifespan: seed, istoric, ceas
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


def auth(username: str) -> dict:
    return {"Authorization": f"Bearer {username}"}      # se schimbă când vin tokenurile reale
```

De ce merge: setările se citesc în `create_app()`, iar motorul bazei de date se creează în `lifespan`
(secțiunile 5 și 6), deci fiecare test primește baza lui, într-un folder temporar. `ASGITransport` nu pornește
singur `lifespan`; de aceea folosim `LifespanManager` din `asgi-lifespan`. Fixture-ul e verificat: trei teste la
rând primesc fiecare baza lor, cu seed-ul făcut.

În teste, `JWT_SECRET` se setează și el cu `monkeypatch.setenv`, fiindcă e obligatoriu.

---

## 14. Git

### Ramurile

- `main` e mereu pornibil: `uv run uvicorn …` pornește și `scripts/smoke.py` trece.
- O ramură pe funcționalitate, scurtă (cel mult 1–2 ore): `be/<ce>`, de exemplu `be/clock`, `be/immune`,
  `be/link-queue`. Securitatea: `sec/<ce>`.
- **PR mic** (sub ~300 de rânduri). Celălalt de pe backend îl citește în cel mult 10 minute; dacă nu poate, îl
  aprobă cine e liber. Merge cu **squash**.
- Înainte de PR: `git pull --rebase origin main`, `uv run ruff format`, `uv run ruff check`, `uv run pytest`,
  `uv run --project backend python scripts/smoke.py`.

### Mesajele de commit

Prefix după folder, apoi ce face: `backend: regula NightSignal`, `backend: coada navă–Pământ`,
`contract: câmp nou initials pe User`, `security: sigilarea pachetelor`.

### Unde ne putem călca și cum evităm

| Fișier | Risc | Regula |
|---|---|---|
| `app/schemas.py` | îl folosește și frontend-ul | doar câmpuri **opționale** noi fără anunț; orice altceva se anunță în chat, apoi `scripts/build_docs.py` |
| `app/main.py` | lifespan, routere | îl ține Backend A; B îi cere schimbări |
| `app/db/models/` | tabele noi | fiecare își editează doar fișierul domeniului lui |
| `app/deps.py` | autentificare | Backend A + securitatea |
| `pyproject.toml`, `uv.lock` | dependențe noi | `uv add` într-un PR separat, mic; conflictul pe `uv.lock` se rezolvă rulând din nou `uv lock` |
| `data/` | formatul fișierelor | schimbarea de format se anunță; conținutul se poate corecta oricând |

---

## 15. Planul pe ore

**A** = Backend A (fundație, cereri, coadă) · **B** = Backend B (simulator, motor, piloni).
Secțiunile din paranteză trimit la `BACKEND_SARCINI.md`.

| Ore | A | B | Punct de control |
|---|---|---|---|
| **0–1** | `uv sync`, `config.py`, `clock.py`, `db/session.py`, `db/base.py` (`create_app()` și `lifespan` există deja) | `engine/types.py`; accesul motorului la praguri prin `app.state.data.params` (`datafiles.py` există) | împreună cu securitatea: semnăturile funcțiilor. Cu AI: forma `/chat`. Cu data: formatul fișierelor |
| **1–2** | tabelele (`db/models/`), `ids.py`, `seed_users`, `get_session` în `deps.py` | `data/scenario/scenario.json`, schelet `simulator/scenario.py` | **serverul pornește pe bază reală; `smoke.py` trece (încă pe mock)** |
| **2–4** | autentificare reală (§2), misiune și medii (§3) | simulatorul (§4): zilele 1–96 în bază; baseline (§5) | |
| **4–6** | check-in (§10), `services/pipeline.py` | Santinela (§8), triaj (§11), `replay_engine` | **alerta lui cm-2 apare în ziua 95 din motor, nu din mock** |
| **6–8** | tabloul de bord, panouri, serii, derulator (§12) | Tastatura și PVT (§6), decalajul de percepție (§10) | |
| **8–10** | evenimente live (§15), `mission_ticker`; scoaterea mock-ului din routerele terminate | cauza de mediu și semnalele încrucișate (§11), testele 1–3 | |
| **10** | **integrare cap-coadă cu frontend-ul**: login → tablou de bord → check-in → alertă → escaladare | | firul din `contract/README.md` §7.6, până la nivelul 2 |
| **10–13** | coada navă–Pământ (§13), `link_scheduler`, cu sigilarea securității | Inima (§7), Încărcarea (§9) | |
| **12** | **punct de decizie**: ce nu merge se taie (secțiunea 17) | | |
| **13–16** | puntea AI (§16), `/sim/reset`, demo (§17) | radiații și furtuna (§14), `recheck_loop`, testele 4–5 | **firul complet până la răspunsul Pământului** |
| **16–18** | dovezi și jurnal (§17), testul 6, ecranul Evidence alimentat | reglarea scenariului pentru demo, performanța pornirii | **demo complet, fără mock nicăieri** |
| **18–21** | bug-uri, video de rezervă | bug-uri, repetiția demo-ului cu `/sim/reset` | |
| **21–24** | repetiții, trimiterea proiectului | repetiții | |

**Scoaterea mock-ului:** la fiecare endpoint terminat, ștergi din `examples.py` ce nu mai folosește nimeni.
Până la ora 16, `examples.py` trebuie să fie gol sau șters. `grep -r "examples" app/routers` arată ce a rămas.

---

## 16. Convenții de cod

- **Nume:** în engleză în cod (`crew_id`, `night_signal`), în română doar textele pentru utilizator.
- **Textele pentru utilizator** (titluri de alerte, explicații, mesaje de eroare) se construiesc în servicii sau
  în motor, complete, în română, gata de afișat. Frontend-ul nu le compune.
- **Erorile:** `raise ApiError(status, code, mesaj, details)` din `deps.py`. Codurile sunt fixe (`contract/README.md`,
  secțiunea 5). Fără `HTTPException` direct.
- **Tipuri:** adnotări peste tot; `Mapped[...]` în modele; modelele din `schemas.py` ca `response_model`.
- **Conversia tabel → contract:** o funcție `to_schema()` în serviciu, nu în router.
- **Log-uri:** `logging.getLogger(__name__)`; fără `print`. **Niciodată** parole, tokenuri sau conținutul
  pachetelor în log-uri.
- **Datele-oră:** doar `clock.now()` și `datetime(..., tzinfo=UTC)`.
- **Funcții mici:** dacă o funcție nu încape pe un ecran, se împarte.

---

## 17. Riscuri și ce tăiem

| Risc | Semn | Ce facem |
|---|---|---|
| „database is locked” | erori la scrieri simultane | WAL + `busy_timeout` (deja în configurare); tranzacții scurte; nicio tranzacție deschisă în timpul unui `await` lung |
| `MissingGreenlet` | eroare la accesul unei relații | lipsește `selectinload(...)` în interogare; `lazy="raise"` arată linia |
| pornire lentă | peste 10 secunde | generarea în memorie + `add_all`; mai puține metrici pe zi în istoric |
| motorul dă altceva decât scenariul | alerta lui cm-2 nu apare în ziua 95 | testul 1 din secțiunea 13; reglăm scenariul, nu pragul |
| securitatea întârzie | funcțiile reale lipsesc la ora 12 | rămân variantele provizorii, dar **nu le prezentăm ca reale** |
| integrarea de la ora 10 nu merge | frontend-ul nu vede datele | endpoint-urile neterminate rămân pe mock; nu blocăm frontend-ul |

**Ordinea în care tăiem**, dacă la ora 12 suntem în urmă (din `BACKEND_SARCINI.md`, secțiunea 18):

1. Inima (§7) rămâne pe date fixe, marcate „simulat”;
2. proiecția osoasă din Încărcarea (§9);
3. `recheck_loop` (reverificarea automată);
4. pachetul DONKI din furtună (rămâne alerta de la dozimetru);
5. `jump_to_day` (rămâne doar derulatorul).

**Nu tăiem niciodată:** Santinela, decalajul de percepție, coada cu întârziere, conturile separate, pachetul
falsificat respins.

---

## 18. Comenzi

```bash
# din backend/
uv sync                                          # instalează exact ce e în uv.lock
uv add <pachet>                                  # dependență nouă (PR separat)
uv run uvicorn app.main:app --reload --port 8000 # pornește; baza se recreează la fiecare pornire
uv run pytest                                    # toate testele
uv run pytest tests/engine -q                    # doar motorul, rapid
uv run ruff format && uv run ruff check --fix    # stil

# din rădăcina repo-ului
uv run --project backend python scripts/smoke.py       # contractul
uv run --project backend python scripts/build_docs.py  # după o schimbare în schemas.py

# demo
curl -X POST localhost:8000/api/v1/sim/reset -H "Authorization: Bearer <token medic>"
```

Variabilele din `.env` folosite de backend:

| Variabilă | Implicit | Ce face |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./shadow.sqlite` | fișierul bazei de date |
| `RESET_DB_ON_START` | `true` | șterge baza la pornire |
| `TIME_SCALE` | `60` | viteza ceasului misiunii |
| `DATA_DIR` | `../data` | de unde se citesc pragurile, catalogul, textele, scenariul |
| `JWT_SECRET` | — | obligatoriu; pornirea se oprește fără el |
| `LINK_AES_KEY_B64` | — | cheia legăturii; o generează `security/keys/generate_keys.py` |
| `AI_URL` | `http://localhost:8001` | serviciul AI |
| `CORS_ORIGINS` | `http://localhost:3000` | adresa frontend-ului |
