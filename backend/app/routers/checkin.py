from fastapi import APIRouter, Depends, Query

from .. import examples as ex
from ..deps import CREW, ERRORS, crew_access, current_user, publish, roles
from ..schemas import Checkin, CheckinCreate, CheckinResult, CheckinSchema, FieldRejection, RejectionKind, User

router = APIRouter(tags=["4. Check-in"])
E = {k: ERRORS[k] for k in (401, 403, 404, 422)}


@router.get("/checkin/schema", response_model=CheckinSchema, summary="Câmpurile check-in-ului", responses={401: ERRORS[401]}, openapi_extra=roles(*CREW))
async def checkin_schema(user: User = Depends(current_user)):
    """Lista câmpurilor, cu textele „Cum se măsoară”, „Ce înseamnă” și „De ce contează în spațiu” și cu limitele de
    plauzibilitate (`min`/`max`). Frontend-ul construiește formularul din acest răspuns; nu țineți textele în cod."""
    return ex.CHECKIN_SCHEMA


@router.post("/crew/{crew_id}/checkins", response_model=CheckinResult, status_code=201, summary="Trimite check-in-ul de dimineață", responses=E, openapi_extra=roles(*CREW))
async def create_checkin(crew_id: str, body: CheckinCreate, user: User = Depends(crew_access)):
    """Salvează check-in-ul zilei. **Un singur check-in pe zi de misiune**: al doilea îl înlocuiește pe primul.

    Ce face backend-ul, în ordine:
    1. validează fiecare câmp față de `min`/`max` din schemă; câmpurile imposibile NU dau eroare 422, ci apar în
       `rejected` și se salvează ca `null` (restul check-in-ului rămâne valid);
    2. compară valorile cu baseline-ul personal;
    3. recalculează decalajul de percepție;
    4. rulează triajul și creează alerte, dacă e cazul;
    5. actualizează seria de zile.

    **SSE:** `dashboard.changed`, plus `alert.created` pentru fiecare alertă nouă."""
    rejected, values = [], body.model_copy()
    limits = {i.key: i for i in ex.CHECKIN_SCHEMA.indicators if i.input == "number"}
    for key, ind in limits.items():
        v = getattr(body, key)
        if v is not None and not (ind.min <= v <= ind.max):
            rejected.append(FieldRejection(field=key, value=v, reason=RejectionKind.implausible,
                                           message=f"{ind.label}: {v} {ind.unit} e în afara intervalului posibil ({ind.min}–{ind.max}). Măsoară din nou."))
            setattr(values, key, None)
    checkin = Checkin(id="ck-0096", crew_id=crew_id, mission_day=ex.MISSION.mission_day, created_at=ex.MISSION.sim_now, values=values)
    publish("dashboard.changed", {"reason": "checkin"}, crew_id)
    return CheckinResult(checkin=checkin, rejected=rejected, perception_gap=ex.GAP.model_copy(update={"self_reported_mood": body.mood, "self_score": body.mood * 20.0}),
                         alerts_created=[], streak=ex.STREAKS[0], message="Check-in salvat. 12 zile la rând.")


@router.get("/crew/{crew_id}/checkins", response_model=list[Checkin], summary="Istoricul check-in-urilor", responses=E, openapi_extra=roles(*CREW))
async def list_checkins(crew_id: str, from_day: int = Query(default=1, ge=1), to_day: int = Query(default=140, ge=1), user: User = Depends(crew_access)):
    """Check-in-urile din interval, cele mai noi primele."""
    return [ex.CHECKIN.model_copy(update={"crew_id": crew_id})]


@router.get("/crew/{crew_id}/checkins/today", response_model=Checkin | None, summary="Check-in-ul de azi", responses=E, openapi_extra=roles(*CREW))
async def today_checkin(crew_id: str, user: User = Depends(crew_access)):
    """Întoarce check-in-ul zilei curente sau `null` dacă nu a fost făcut. Folosiți-l ca să decideți dacă afișați formularul."""
    return ex.CHECKIN.model_copy(update={"crew_id": crew_id})
