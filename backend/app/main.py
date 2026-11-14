import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.engine import make_url
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import schemas
from .clock import clock
from .config import get_settings
from .datafiles import load_all
from .db import models  # noqa: F401  (registers every table on Base.metadata)
from .db import session as db
from .db.base import Base
from .db.seed import seed_crew_and_users, seed_history
from .deps import ApiError
from .link import queue as link_queue
from .link import scheduler as link_scheduler
from .routers import (
    ai,
    alerts,
    auth,
    behavioral,
    checkin,
    crew,
    demo,
    events,
    exercise,
    link,
    mission,
    radiation,
    security,
)
from .security import keys as security_keys
from .services import access, pipeline, security_log
from .services import alerts as alerts_service
from .services import exercise as exercise_service
from .services import mission as mission_service
from .services import radiation as radiation_service
from .simulator import live

API_PREFIX = "/api/v1"
VERSION = "1.2.0"

log = logging.getLogger(__name__)
startup_log = logging.getLogger("uvicorn.error")  # uvicorn only prints its own loggers by default

BACKEND_DIR = Path(__file__).resolve().parents[1]
USERS_SEED = BACKEND_DIR / "seed" / "users.json"


def resolve_data_dir(data_dir: str) -> Path:
    path = Path(data_dir)
    return path if path.is_absolute() else (BACKEND_DIR / path).resolve()


def delete_sqlite_files(url: str) -> None:
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite" or parsed.database in (None, "", ":memory:"):
        return
    for suffix in ("", "-wal", "-shm"):
        Path(parsed.database + suffix).unlink(missing_ok=True)


async def db_status() -> str:
    if db.engine is None:
        return "unavailable"
    try:
        async with db.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        log.exception("database health check failed")
        return "error"
    return "ok"


async def bootstrap(app: FastAPI) -> None:
    """Tables, clock (day 96, 07:00), accounts, history, replay of the engine, radiation background. Used at
    startup and by POST /sim/reset (after the tables were emptied)."""
    settings, data = app.state.settings, app.state.data
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    scenario = data.scenario
    clock.start(
        mission_start=scenario.start, day=scenario.start_day, time_hhmm=scenario.start_time, scale=settings.time_scale
    )
    async with db.SessionLocal() as s:
        await seed_crew_and_users(s, str(USERS_SEED))
        await mission_service.init_environment(s, data)
        await seed_history(s, data, until_day=scenario.start_day, not_after=clock.now())
        await exercise_service.backfill(s, until_day=scenario.start_day)
        await pipeline.replay_history(s, until_day=scenario.start_day, data=data)
        await radiation_service.seed_readings(s, data)
        await s.commit()


async def wipe(app: FastAPI) -> None:
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def start_tasks(app: FastAPI) -> None:
    if not app.state.settings.background_tasks:
        app.state.tasks = []
        return
    data = app.state.data
    app.state.tasks = [
        asyncio.create_task(mission_service.mission_ticker(), name="mission_ticker"),
        asyncio.create_task(link_scheduler.link_scheduler(data), name="link_scheduler"),
        asyncio.create_task(live.live_simulator(data), name="live_simulator"),
        asyncio.create_task(alerts_service.recheck_loop(data), name="recheck_loop"),
    ]


async def stop_tasks(app: FastAPI) -> None:
    tasks = getattr(app.state, "tasks", [])
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    app.state.tasks = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = app.state.settings
    if settings.reset_db_on_start:
        delete_sqlite_files(settings.database_url)
    started = time.perf_counter()
    engine = db.init_engine(settings.database_url)
    try:
        app.state.data = load_all(resolve_data_dir(settings.data_dir))
        app.state.keys = security_keys.load_keys(link_aes_key_b64=settings.link_aes_key_b64)
        link_queue.configure(app.state.keys)
        app.state.bootstrap, app.state.wipe = bootstrap, wipe
        app.state.start_tasks, app.state.stop_tasks = start_tasks, stop_tasks
        await bootstrap(app)
        start_tasks(app)
        # once per process, not restarted by /sim/reset; the thread finishes on its own
        app.state.engine_tests = (
            asyncio.create_task(security_log.run_engine_tests(), name="engine_tests")
            if settings.background_tasks
            else None
        )
        startup_log.info("SHADOW startup finished in %.2f s", time.perf_counter() - started)
        yield
    finally:
        await stop_tasks(app)
        await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SHADOW API",
        version=VERSION,
        description="The contract between the SHADOW frontend and backend (NASA Space Apps 2026). "
        "Decision-support prototype, not a medical device. Full documentation: contract/api/README.md.",
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
    for r in (auth, mission, crew, checkin, behavioral, exercise, alerts, link, radiation, ai, security, demo, events):
        app.include_router(r.router, prefix=API_PREFIX)

    @app.get("/health", tags=["0. Server health"], summary="Is the server up?")
    async def health():
        """No authentication. Used by Docker Compose and by the frontend at startup.
        `mode` is `mock` while some endpoints still serve example data, then `real`.
        `db` is `ok` when the database answers a `SELECT 1`."""
        return {"ok": True, "version": app.version, "mode": "mock", "db": await db_status()}

    app.add_exception_handler(ApiError, api_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(StarletteHTTPException, http_error)
    app.add_exception_handler(Exception, unexpected)
    app.openapi = lambda: custom_openapi(app)
    return app


def _err(status: int, code: str, message: str, details=None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details}})


async def api_error(request: Request, e: ApiError):
    if e.status == 403:
        await access.record_denied(request)
    return _err(e.status, e.code, e.message, e.details)


async def validation_error(_: Request, e: RequestValidationError):
    fields = [{"field": ".".join(str(p) for p in err["loc"][1:]), "problem": err["msg"]} for err in e.errors()]
    return _err(422, "validation_error", "The submitted data does not match the contract.", {"fields": fields})


async def http_error(_: Request, e: StarletteHTTPException):
    code = {404: "not_found", 405: "method_not_allowed"}.get(e.status_code, "http_error")
    return _err(e.status_code, code, str(e.detail))


async def unexpected(_: Request, e: Exception):
    return _err(500, "internal_error", "Unexpected server error.")


def custom_openapi(app: FastAPI):
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi

    spec = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
    comps = spec.setdefault("components", {})
    comps["securitySchemes"] = {"bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}
    for model in (schemas.SseEvent, schemas.MissionTick):
        js = model.model_json_schema(ref_template="#/components/schemas/{model}")
        js.pop("$defs", None)
        comps["schemas"][model.__name__] = js
    for path in spec["paths"].values():
        for op in path.values():
            r = op.get("x-roles", [])
            if r and r != ["public"] and r != ["device"]:
                op["security"] = [{"bearerAuth": []}]
            if r:
                op["description"] = f"**Roluri permise:** {', '.join(f'`{x}`' for x in r)}\n\n" + op.get(
                    "description", ""
                )
    app.openapi_schema = spec
    return spec


app = create_app()
