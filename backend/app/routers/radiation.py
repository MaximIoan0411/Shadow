from datetime import timedelta

from fastapi import APIRouter, Depends, Query

from .. import examples as ex
from ..deps import ALL, CREW, ERRORS, current_user, publish, require_roles, roles
from ..schemas import RadiationPoint, RadiationSeries, RadiationStatus, SepEvent, ShelterAck, User

router = APIRouter(prefix="/radiation", tags=["9. Radiații și furtuna solară"])

STATE = {"storm": False, "sheltered": False}


def current() -> RadiationStatus:
    if not STATE["storm"]:
        return ex.RAD_QUIET
    s = ex.RAD_STORM.model_copy(update={"sheltered": STATE["sheltered"]})
    if not STATE["sheltered"]:
        s.sheltered_since = None
    return s


@router.get("/status", response_model=RadiationStatus, summary="Starea radiațiilor acum", responses={k: ERRORS[k] for k in (401, 403)}, openapi_extra=roles(*CREW))
async def radiation_status(user: User = Depends(require_roles(*CREW))):
    """Rata dozei la dozimetrul de la bord, media pe 24 h, dacă e alertă și dacă echipajul e în adăpost.

    `lead_minutes` se completează când sosește avertizarea DONKI de pe Pământ: e numărul de minute cu care SHADOW a
    fost mai rapid. Afișați-l mare; e cifra din pitch.

    Rolul `earth` NU are acces: Pământul nu vede dozimetrul navei în timp real, ci doar ce ajunge prin coadă."""
    return current()


@router.get("/series", response_model=RadiationSeries, summary="Curba dozei (grafic)", responses={k: ERRORS[k] for k in (401, 403)}, openapi_extra=roles(*CREW))
async def radiation_series(hours: float = Query(default=24, gt=0, le=240, description="Câte ore de misiune în urmă."),
                     step_min: int = Query(default=10, ge=1, le=120), user: User = Depends(require_roles(*CREW))):
    """Punctele pentru graficul dozei. Reîncărcați la SSE `radiation.reading` (vine cel mult o dată la 2 secunde reale)."""
    n = int(hours * 60 / step_min)
    pts = []
    for i in range(n):
        t = ex.NOW - timedelta(minutes=step_min * (n - 1 - i))
        storm = STATE["storm"] and i >= n - 3
        pts.append(RadiationPoint(t=t, dose_rate_usv_h=[150.0, 320.0, 412.0][i - (n - 3)] if storm else 65.8 + (i % 5) * 0.4,
                                  mean_24h_usv_h=66.0, sheltered=storm and STATE["sheltered"]))
    return RadiationSeries(points=pts)


@router.get("/events", response_model=list[SepEvent], summary="Evenimentele DONKI disponibile", responses={401: ERRORS[401]}, openapi_extra=roles(*ALL))
async def radiation_events(user: User = Depends(current_user)):
    """Evenimentele reale NASA DONKI încărcate din fișier (offline). Momentan unul: 11 mai 2024."""
    return [ex.SEP]


@router.post("/shelter-ack", response_model=RadiationStatus, summary="„Sunt în adăpost”", responses={k: ERRORS[k] for k in (401, 403, 422)}, openapi_extra=roles(*CREW))
async def shelter_ack(body: ShelterAck, user: User = Depends(require_roles(*CREW))):
    """Astronautul confirmă că a ajuns în adăpost (sau că a ieșit). Din acest moment simulatorul aplică factorul de
    ecranare, iar ora se salvează pentru calculul `lead_minutes`.

    **SSE:** `radiation.reading`."""
    STATE["sheltered"] = body.sheltered
    publish("radiation.reading", current())
    return current()
