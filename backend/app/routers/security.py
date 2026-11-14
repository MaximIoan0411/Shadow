
from fastapi import APIRouter, Depends, Query

from .. import examples as ex
from ..deps import ALL, CREW, ERRORS, current_user, publish, require_roles, roles
from ..schemas import (
    AccessLogEntry,
    IngestResult,
    MeasurementIngest,
    Parameter,
    Rejection,
    RejectionKind,
    Role,
    TestReport,
    User,
)

router = APIRouter(tags=["11. Securitate și dovezi"])


@router.get("/access-log", response_model=list[AccessLogEntry], summary="Jurnalul de acces", responses={k: ERRORS[k] for k in (401, 403)}, openapi_extra=roles(*CREW))
async def access_log(crew_id: str | None = Query(default=None, description="Astronaut: se ignoră, vede mereu doar accesul la datele lui."),
               limit: int = Query(default=50, ge=1, le=500), user: User = Depends(require_roles(*CREW))):
    """Cine a citit ce. Astronautul vede cine i-a accesat datele; ofițerul medical vede tot jurnalul.
    Jurnalul doar se adaugă: fiecare intrare conține hash-ul celei dinainte (`prev_hash`), deci nu poate fi modificat pe ascuns."""
    target = user.crew_id if user.role == Role.astronaut else crew_id
    return [e for e in ex.ACCESS_LOG if target is None or e.crew_id == target][:limit]


@router.get("/security/rejections", response_model=list[Rejection], summary="Date și pachete respinse", responses={k: ERRORS[k] for k in (401, 403)}, openapi_extra=roles(*CREW))
async def rejections(limit: int = Query(default=50, ge=1, le=500), user: User = Depends(require_roles(*CREW))):
    """Valorile imposibile, senzorii „înghețați”, semnăturile invalide și pachetele retrimise."""
    return ex.REJECTIONS[:limit]


@router.post("/ingest/measurements", response_model=IngestResult, summary="Primește o măsurătoare de la un dispozitiv", responses={422: ERRORS[422]}, openapi_extra={"x-roles": ["device"]})
async def ingest(body: MeasurementIngest):
    """**Nu e pentru frontend.** Îl apelează simulatorul și dispozitivele. Nu folosește JWT: autentificarea este
    semnătura Ed25519 a dispozitivului, verificată cu cheia publică înregistrată pentru `device_id`.

    Verificări, în ordine: semnătura → plauzibilitatea valorii → senzor înghețat (aceeași valoare de prea multe ori).
    O măsurătoare respinsă întoarce tot 200, cu `accepted = false`, și apare în `/security/rejections`.

    **SSE:** `measurement.rejected` la respingere."""
    if not (20 <= body.value <= 250) and body.metric_key.endswith("_bpm"):
        rej = Rejection(id="rj-0004", at=body.measured_at, kind=RejectionKind.implausible, source=body.device_id, crew_id=body.crew_id,
                        metric_key=body.metric_key, value=body.value, message=f"Valoare imposibilă: {body.value} {body.unit}")
        publish("measurement.rejected", rej, body.crew_id)
        return IngestResult(accepted=False, rejection=rej)
    return IngestResult(accepted=True)


@router.get("/evidence/tests", response_model=TestReport, summary="Rezultatele testelor automate", responses={401: ERRORS[401]}, openapi_extra=roles(*ALL))
async def evidence_tests(user: User = Depends(current_user)):
    """Ultimul raport pytest pe motorul de protocoale, pentru ecranul Evidence."""
    return ex.TEST_REPORT


@router.get("/evidence/parameters", response_model=list[Parameter], summary="Pragurile și sursele lor", responses={401: ERRORS[401]}, openapi_extra=roles(*ALL))
async def evidence_parameters(topic: str | None = Query(default=None, description="comportamental / cardiovascular / imunitar / oase_muschi / radiatii / comunicare"),
                        key_only: bool = Query(default=False, description="Doar pragurile folosite direct de motorul de triaj."),
                        user: User = Depends(current_user)):
    """Conținutul `parameters.json`: fiecare prag cu valoare, unitate, explicație și sursă, marcat verificat/neverificat și publicat/derivat."""
    return [p for p in ex.PARAMETERS if (topic is None or p.topic == topic) and (not key_only or p.is_key_threshold)]
