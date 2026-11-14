"""SHADOW API — scheletul contractului.

Rulează ca MOCK SERVER: toate endpoint-urile există și întorc date de exemplu valide, iar textele, mediile,
catalogul și pragurile vin deja din data/. Backend-ul înlocuiește pe rând corpul fiecărei funcții cu logica
reală, FĂRĂ să schimbe semnăturile (cale, parametri, modele). Așa frontend-ul nu se strică niciodată.

    uv run uvicorn app.main:app --reload --port 8000
    http://localhost:8000/docs   ← documentație interactivă (Swagger)

Arhitectura țintă (create_app + lifespan + task-uri din fundal): backend/PLAN_DE_ATAC_BACKEND.md, secțiunile 5–10.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import schemas
from .deps import ApiError
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

API_PREFIX = "/api/v1"
VERSION = "1.2.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MOCK: nimic de pornit. REAL (planul de atac, secțiunea 6), în ordine:
    #   1. ștergerea bazei (RESET_DB_ON_START) + init_engine + create_all
    #   2. load_all(DATA_DIR) din app/datafiles.py → app.state.data
    #   3. seed_users, seed_history(until_day=scenario.start_day), replay_engine
    #   4. clock.start(day=scenario.start_day, ...)
    #   5. task-urile: link_scheduler, mission_ticker, live_simulator, recheck_loop
    yield
    #   la oprire: anularea task-urilor, engine.dispose()


def create_app() -> FastAPI:
    """Aplicația se construiește aici (nu la import), ca testele să poată schimba setările înainte."""
    app = FastAPI(
        title="SHADOW API",
        version=VERSION,
        description="Contractul dintre frontend și backend pentru SHADOW (NASA Space Apps 2026). "
                    "Prototip de sprijin pentru decizie, nu dispozitiv medical. Documentația completă: contract/api/README.md.",
        openapi_url=f"{API_PREFIX}/openapi.json", docs_url="/docs", redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
                       allow_methods=["*"], allow_headers=["*"])
    for r in (auth, mission, crew, checkin, behavioral, exercise, alerts, link, radiation, ai, security, demo, events):
        app.include_router(r.router, prefix=API_PREFIX)

    @app.get("/health", tags=["0. Sănătatea serverului"], summary="Serverul răspunde?")
    async def health():
        """Fără autentificare. Folosit de Docker Compose și de frontend la pornire.
        `mode` e `mock` cât timp există endpoint-uri pe date de exemplu, apoi `real`."""
        return {"ok": True, "version": app.version, "mode": "mock"}

    app.add_exception_handler(ApiError, api_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(StarletteHTTPException, http_error)
    app.add_exception_handler(Exception, unexpected)
    app.openapi = lambda: custom_openapi(app)
    return app


# ------------------------------------------------------------------ erori într-o singură formă
def _err(status: int, code: str, message: str, details=None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details}})


async def api_error(_: Request, e: ApiError):
    return _err(e.status, e.code, e.message, e.details)


async def validation_error(_: Request, e: RequestValidationError):
    fields = [{"field": ".".join(str(p) for p in err["loc"][1:]), "problem": err["msg"]} for err in e.errors()]
    return _err(422, "validation_error", "Datele trimise nu respectă contractul.", {"fields": fields})


async def http_error(_: Request, e: StarletteHTTPException):
    code = {404: "not_found", 405: "method_not_allowed"}.get(e.status_code, "http_error")
    return _err(e.status_code, code, str(e.detail))


async def unexpected(_: Request, e: Exception):
    return _err(500, "internal_error", "Eroare neașteptată pe server.")


# ------------------------------------------------------------------ OpenAPI: securitate + modelele SSE
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
                op["description"] = f"**Roluri permise:** {', '.join(f'`{x}`' for x in r)}\n\n" + op.get("description", "")
    app.openapi_schema = spec
    return spec


app = create_app()          # pentru `uvicorn app.main:app`
