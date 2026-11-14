
from fastapi import APIRouter, Depends, Query

from .. import examples as ex
from ..deps import CREW, ERRORS, ApiError, crew_access, current_user, publish, require_roles, roles
from ..schemas import (
    Alert,
    AlertBrief,
    AlertHistoryEntry,
    AlertState,
    AlertTopic,
    EscalateRequest,
    Recommendation,
    ResolveRequest,
    Role,
    StepUpdate,
    User,
)

router = APIRouter(tags=["7. Alerte, triaj, catalog"])
E = {k: ERRORS[k] for k in (401, 403, 404, 422)}
E409 = {**E, 409: ERRORS[409]}


def _get(alert_id: str, user: User) -> Alert:
    a = ex.ALERTS.get(alert_id)
    if not a:
        raise ApiError(404, "not_found", f"Nu există alerta {alert_id}.")
    if user.role == Role.astronaut and a.crew_id != user.crew_id:
        raise ApiError(403, "forbidden", "Nu ai acces la alerta altui membru al echipajului.")
    if user.role == Role.cmo and a.level < 2 and a.crew_id != user.crew_id:
        raise ApiError(403, "forbidden", "Ofițerul medical vede doar alertele de nivel 2 și 3.")
    return a


@router.get("/crew/{crew_id}/alerts", response_model=list[AlertBrief], summary="Alertele unui membru al echipajului", responses=E, openapi_extra=roles(*CREW))
async def list_alerts(crew_id: str,
                state: AlertState | None = Query(default=None, description="Filtru. Fără parametru = toate cele nerezolvate."),
                topic: AlertTopic | None = None, user: User = Depends(crew_access)):
    """Lista scurtă, cele mai grave primele. Ofițerul medical primește aici doar alertele de nivel ≥ 2 ale altor membri."""
    out = [ex.brief(a) for a in ex.ALERTS.values() if a.crew_id == crew_id and (state is None or a.state == state) and (topic is None or a.topic == topic)]
    if user.role == Role.cmo and user.crew_id != crew_id:
        out = [a for a in out if a.level >= 2]
    return sorted(out, key=lambda a: -a.level)


@router.get("/cmo/queue", response_model=list[AlertBrief], summary="Coada ofițerului medical", responses={k: ERRORS[k] for k in (401, 403)}, openapi_extra=roles(Role.cmo))
async def cmo_queue(user: User = Depends(require_roles(Role.cmo))):
    """Toate alertele de nivel 2 și 3 nerezolvate, din tot echipajul. Ecranul principal al rolului `cmo`."""
    return [ex.brief(a) for a in ex.ALERTS.values() if a.level >= 2 and a.state != AlertState.resolved]


@router.get("/alerts/{alert_id}", response_model=Alert, summary="Alerta completă", responses=E, openapi_extra=roles(*CREW))
async def get_alert(alert_id: str, user: User = Depends(require_roles(*CREW))):
    """Dovezile, cauza (individuală sau de mediu), recomandarea din catalog cu sursa ei, planul de acțiune, data
    reverificării și istoricul. Fiecare citire de către ofițerul medical se scrie în jurnalul de acces."""
    return _get(alert_id, user)


@router.post("/alerts/{alert_id}/ack", response_model=Alert, summary="Confirmă că ai văzut alerta", responses=E409, openapi_extra=roles(Role.astronaut, Role.cmo))
async def ack_alert(alert_id: str, user: User = Depends(require_roles(*CREW))):
    """Trece alerta din `active` în `acknowledged`. Nu se poate apela pe o alertă deja escaladată sau rezolvată (409 `invalid_state`).

    **SSE:** `alert.updated`."""
    a = _get(alert_id, user)
    if a.state != AlertState.active:
        raise ApiError(409, "invalid_state", f"Alerta e deja în starea {a.state.value}.")
    a.state = AlertState.acknowledged
    a.history.append(AlertHistoryEntry(at=ex.MISSION.sim_now, actor=user.display_name, role=user.role, action="acknowledged"))
    publish("alert.updated", ex.brief(a), a.crew_id)
    return a


@router.put("/alerts/{alert_id}/plan/steps/{step_id}", response_model=Alert, summary="Bifează un pas din plan", responses=E, openapi_extra=roles(*CREW))
async def update_step(alert_id: str, step_id: str, body: StepUpdate, user: User = Depends(require_roles(*CREW))):
    """Bifează sau debifează un pas al planului de acțiune.

    **SSE:** `alert.updated`."""
    a = _get(alert_id, user)
    step = next((s for s in a.plan_steps if s.id == step_id), None)
    if not step:
        raise ApiError(404, "not_found", f"Nu există pasul {step_id}.")
    step.done, step.done_at = body.done, (ex.MISSION.sim_now if body.done else None)
    publish("alert.updated", ex.brief(a), a.crew_id)
    return a


@router.post("/alerts/{alert_id}/escalate", response_model=Alert, summary="Escaladează alerta", responses=E409, openapi_extra=roles(*CREW))
async def escalate(alert_id: str, body: EscalateRequest, user: User = Depends(require_roles(*CREW))):
    """Urcă alerta un nivel.

    * `to_level = 2` — astronautul o trimite ofițerului medical. Apare în `/cmo/queue`.
    * `to_level = 3` — **doar rolul `cmo`**. Backend-ul creează automat un pachet semnat și criptat în coada spre
      Pământ și pune id-ul lui în `packet_id`. Nu mai trebuie apelat `/link/outbox`.

    Nivelul nu poate coborî (409 `invalid_state`). Alertele critice pot fi escaladate și automat de motorul de triaj.

    **SSE:** `alert.updated`, iar la nivelul 3 și `packet.sent` când se deschide fereastra."""
    a = _get(alert_id, user)
    if body.to_level == 3 and user.role != Role.cmo:
        raise ApiError(403, "forbidden", "Doar ofițerul medical poate trimite o alertă pe Pământ.")
    if body.to_level < a.level or (body.to_level == a.level and a.state == AlertState.escalated):
        raise ApiError(409, "invalid_state", f"Alerta e deja la nivelul {a.level}.")
    a.level, a.state = body.to_level, AlertState.escalated
    if body.to_level == 3:
        a.packet_id = "pk-0007"
    a.history.append(AlertHistoryEntry(at=ex.MISSION.sim_now, actor=user.display_name, role=user.role, action="escalated", note=body.note))
    publish("alert.updated", ex.brief(a), a.crew_id)
    return a


@router.post("/alerts/{alert_id}/resolve", response_model=Alert, summary="Închide alerta", responses=E, openapi_extra=roles(*CREW))
async def resolve(alert_id: str, body: ResolveRequest, user: User = Depends(require_roles(*CREW))):
    """Astronautul poate închide alertele de nivel 1; cele de nivel 2 și 3 le închide ofițerul medical.
    `outcome = monitoring` păstrează alerta deschisă și mută `recheck_at` cu încă o zi.

    **SSE:** `alert.updated`."""
    a = _get(alert_id, user)
    if a.level >= 2 and user.role != Role.cmo:
        raise ApiError(403, "forbidden", "Alertele de nivel 2 și 3 le închide ofițerul medical.")
    if body.outcome != "monitoring":
        a.state = AlertState.resolved
    a.history.append(AlertHistoryEntry(at=ex.MISSION.sim_now, actor=user.display_name, role=user.role, action="resolved", note=body.note))
    publish("alert.updated", ex.brief(a), a.crew_id)
    return a


@router.get("/catalog/recommendations", response_model=list[Recommendation], summary="Catalogul de recomandări", responses={401: ERRORS[401]}, openapi_extra=roles(*CREW, Role.earth))
async def list_recommendations(topic: AlertTopic | None = None, level: int | None = Query(default=None, ge=1, le=3), user: User = Depends(current_user)):
    """Recomandările scrise de echipă pe baza riscurilor NASA HRP, fiecare cu sursa ei. Medicul AI doar le reformulează."""
    return [r for r in ex.RECOMMENDATIONS if (topic is None or r.topic == topic) and (level is None or r.level == level)]


@router.get("/catalog/recommendations/{rec_id}", response_model=Recommendation, summary="O recomandare din catalog", responses={k: ERRORS[k] for k in (401, 404)}, openapi_extra=roles(*CREW, Role.earth))
async def get_recommendation(rec_id: str, user: User = Depends(current_user)):
    if rec_id not in ex.REC_BY_ID:
        raise ApiError(404, "not_found", f"Nu există recomandarea {rec_id}.")
    return ex.REC_BY_ID[rec_id]
