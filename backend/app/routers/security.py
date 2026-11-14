from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from .. import examples as ex
from ..db.session import get_session
from ..deps import ALL, CREW, ERRORS, current_user, publish, require_roles, roles
from ..schemas import (
    AccessLogEntry,
    IngestResult,
    MeasurementIngest,
    Parameter,
    Rejection,
    RejectionKind,
    TestReport,
    User,
)
from ..services import access

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
async def rejections(limit: int = Query(default=50, ge=1, le=500), user: User = Depends(require_roles(*CREW))):
    """Impossible values, "frozen" sensors, invalid signatures and replayed packets."""
    return ex.REJECTIONS[:limit]


@router.post(
    "/ingest/measurements",
    response_model=IngestResult,
    summary="Receive a measurement from a device",
    responses={422: ERRORS[422]},
    openapi_extra={"x-roles": ["device"]},
)
async def ingest(body: MeasurementIngest):
    """**Not for the frontend.** Called by the simulator and the devices. It does not use a JWT: authentication is
    the device's Ed25519 signature, checked with the public key registered for `device_id`.

    Checks, in order: signature → plausibility of the value → frozen sensor (the same value too many times).
    A rejected measurement still returns 200, with `accepted = false`, and shows up in `/security/rejections`.

    **SSE:** `measurement.rejected` on rejection."""
    if not (20 <= body.value <= 250) and body.metric_key.endswith("_bpm"):
        rej = Rejection(
            id="rj-0004",
            at=body.measured_at,
            kind=RejectionKind.implausible,
            source=body.device_id,
            crew_id=body.crew_id,
            metric_key=body.metric_key,
            value=body.value,
            message=f"Impossible value: {body.value} {body.unit}",
        )
        publish("measurement.rejected", rej, body.crew_id)
        return IngestResult(accepted=False, rejection=rej)
    return IngestResult(accepted=True)


@router.get(
    "/evidence/tests",
    response_model=TestReport,
    summary="Automated test results",
    responses={401: ERRORS[401]},
    openapi_extra=roles(*ALL),
)
async def evidence_tests(user: User = Depends(current_user)):
    """The latest pytest report on the protocol engine, for the Evidence screen."""
    return ex.TEST_REPORT


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
):
    """The content of `parameters.json`: every threshold with value, unit, explanation and source, marked
    verified/unverified and published/derived."""
    return [p for p in ex.PARAMETERS if (topic is None or p.topic == topic) and (not key_only or p.is_key_threshold)]
