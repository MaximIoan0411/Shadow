from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..datafiles import DataBundle
from ..db.session import get_session
from ..deps import ALL, CREW, ERRORS, current_user, get_data, require_roles, roles
from ..schemas import AccessLogEntry, IngestResult, MeasurementIngest, Parameter, Rejection, TestReport, User
from ..services import access, security_log
from ..services.events import publish_all

router = APIRouter(tags=["11. Security and evidence"])


@router.get(
    "/access-log",
    response_model=list[AccessLogEntry],
    summary="Access log",
    responses={k: ERRORS[k] for k in (401, 403)},
    openapi_extra=roles(*CREW),
)
async def access_log(
    crew_id: str | None = Query(
        default=None, description="Astronaut: ignored, they always see only access to their own data."
    ),
    limit: int = Query(default=50, ge=1, le=500),
    user: User = Depends(require_roles(*CREW)),
    session: AsyncSession = Depends(get_session),
):
    """Who read what, newest first. An astronaut sees who accessed their data; the crew medical officer sees the
    whole log. The log is append-only: every entry holds the hash of the previous one (`prev_hash`), so it cannot be
    changed silently."""
    return await access.entries(session, user, crew_id, limit)


@router.get(
    "/security/rejections",
    response_model=list[Rejection],
    summary="Rejected data and packets",
    responses={k: ERRORS[k] for k in (401, 403)},
    openapi_extra=roles(*CREW),
)
async def rejections(
    limit: int = Query(default=50, ge=1, le=500),
    user: User = Depends(require_roles(*CREW)),
    session: AsyncSession = Depends(get_session),
):
    """Impossible values, "frozen" sensors, invalid signatures and replayed packets, newest first."""
    return await security_log.rejections(session, limit, user)


@router.post(
    "/ingest/measurements",
    response_model=IngestResult,
    summary="Receive a measurement from a device",
    responses={422: ERRORS[422]},
    openapi_extra={"x-roles": ["device"]},
)
async def ingest(
    body: MeasurementIngest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """**Not for the frontend.** Called by the simulator and the devices. It does not use a JWT: authentication is
    the device's Ed25519 signature, checked with the public key registered for `device_id`.

    Checks, in order: signature → plausibility of the value → frozen sensor (the same value too many times).
    A rejected measurement still returns 200, with `accepted = false`, and shows up in `/security/rejections`.

    **SSE:** `measurement.rejected` on rejection."""
    signed = await request.json()  # the body as sent: the signature covers exactly these fields and values
    result, events = await security_log.ingest(session, data, request.app.state.keys, body, signed)
    publish_all(events)
    return result


@router.get(
    "/evidence/tests",
    response_model=TestReport,
    summary="Automated test results",
    responses={401: ERRORS[401]},
    openapi_extra=roles(*ALL),
)
async def evidence_tests(user: User = Depends(current_user)):
    """The latest pytest report on the protocol engine, for the Evidence screen (run once at server start)."""
    return security_log.test_report()


@router.get(
    "/evidence/parameters",
    response_model=list[Parameter],
    summary="Thresholds and their sources",
    responses={401: ERRORS[401]},
    openapi_extra=roles(*ALL),
)
async def evidence_parameters(
    topic: str | None = Query(
        default=None, description="comportamental / cardiovascular / imunitar / oase_muschi / radiatii / comunicare"
    ),
    key_only: bool = Query(default=False, description="Only the thresholds used directly by the triage engine."),
    user: User = Depends(current_user),
    data: DataBundle = Depends(get_data),
):
    """The content of `parameters.json`: every threshold with value, unit, explanation and source, marked
    verified/unverified and published/derived."""
    return security_log.parameters(data, topic, key_only)
