
from fastapi import APIRouter, Depends, Query

from .. import examples as ex
from ..deps import CREW, ERRORS, ApiError, crew_access, require_roles, roles
from ..schemas import CrewSummary, Dashboard, MetricSeries, Pillar, PillarDetail, Role, Status, Timeline, User

router = APIRouter(tags=["3. Echipaj și corpul interactiv"])
E = {k: ERRORS[k] for k in (401, 403, 404)}

AS_OF = Query(default=None, ge=1, description="Derulator: starea de la sfârșitul acestei zile. Fără parametru = acum. "
                                              "Trebuie să fie ≤ ziua curentă (zilele viitoare nu există încă) → altfel 422.")


def check_as_of(as_of_day: int | None) -> None:
    if as_of_day is not None and as_of_day > ex.MISSION.mission_day:
        raise ApiError(422, "validation_error", f"Ziua {as_of_day} nu a avut loc încă (ziua curentă: {ex.MISSION.mission_day}).",
                       {"fields": [{"field": "as_of_day", "problem": "în viitor"}]})


@router.get("/crew", response_model=list[CrewSummary], summary="Lista echipajului", responses={k: ERRORS[k] for k in (401, 403)}, openapi_extra=roles(Role.cmo))
async def list_crew(user: User = Depends(require_roles(Role.cmo))):
    """Doar pentru ofițerul medical. Conține doar starea generală, nu valori medicale."""
    # fiecare membru are contul lui; aici apare doar starea generală
    return [CrewSummary(member=c, overall_status=Status.alert if c.id == "cm-2" else Status.ok,
                        active_alerts=2 if c.id == "cm-2" else 0, highest_level=2 if c.id == "cm-2" else None) for c in ex.CREW]


@router.get("/crew/{crew_id}/dashboard", response_model=Dashboard, summary="Tabloul de bord al astronautului", responses=E, openapi_extra=roles(*CREW))
async def dashboard(crew_id: str, as_of_day: int | None = AS_OF, user: User = Depends(crew_access)):
    """**Apelul principal al ecranului astronautului.** Într-un singur răspuns: starea celor 4 piloni (culorile zonelor
    de pe corp), decalajul de percepție, semnalele încrucișate, alerta principală, seriile de zile și reamintirile.

    Reîncărcați-l când primiți SSE `dashboard.changed`, `alert.created` sau `alert.updated`."""
    check_as_of(as_of_day)
    return ex.dashboard_for(crew_id)


@router.get("/crew/{crew_id}/pillars/{pillar}", response_model=PillarDetail, summary="Panoul unei zone a corpului", responses=E, openapi_extra=roles(*CREW))
async def pillar_detail(crew_id: str, pillar: Pillar, as_of_day: int | None = AS_OF, user: User = Depends(crew_access)):
    """Se apelează la click pe o zonă. Conține, în ordinea afișării: funcția părții corpului, pericolul spațial,
    valorile față de baseline, graficul, explicația, planul de acțiune și sursele."""
    check_as_of(as_of_day)
    return ex.pillar_for(crew_id, pillar)


@router.get("/crew/{crew_id}/pillars/{pillar}/series", response_model=MetricSeries, summary="Seria unei metrici (grafic)", responses=E, openapi_extra=roles(*CREW))
async def pillar_series(crew_id: str, pillar: Pillar,
                  metric: str = Query(description="Cheia metricii, ex. `night_pulse_bpm`. Vezi README, „Chei de metrici”."),
                  from_day: int = Query(default=1, ge=1), to_day: int | None = Query(default=None, ge=1, description="Implicit: ziua curentă."),
                  user: User = Depends(crew_access)):
    """Pentru un al doilea grafic sau pentru un interval mai lung decât cel din panou (care are ultimele 10 zile)."""
    detail = ex.pillar_for(crew_id, pillar)
    if metric not in {m.key for m in detail.metrics} | {detail.chart.metric_key}:
        raise ApiError(404, "not_found", f"Metrica {metric} nu există în pilonul {pillar.value}.")
    return detail.chart.model_copy(update={"metric_key": metric})


@router.get("/crew/{crew_id}/timeline", response_model=Timeline, summary="Istoric pe zile (derulator)", responses=E, openapi_extra=roles(*CREW))
async def get_timeline(crew_id: str, from_day: int = Query(default=1, ge=1),
                       to_day: int | None = Query(default=None, ge=1, description="Implicit și maximum: ziua curentă."),
                       user: User = Depends(crew_access)):
    """Starea fiecărui pilon pe fiecare zi **care a avut loc**: de la `from_day` până la ziua curentă (misiunea
    pornește în ziua 96, deci la început sunt 96 de zile). Zilele viitoare nu apar; bara derulatorului arată restul
    până la `total_days` (din `/mission`) ca „încă nu”.

    Se încarcă o dată la pornire și se reîncarcă la `mission.tick` doar când se schimbă `mission_day`.
    Când utilizatorul se oprește pe o zi, reîncărcați `dashboard` și panoul deschis cu `?as_of_day=`."""
    last = min(to_day or ex.MISSION.mission_day, ex.MISSION.mission_day)
    return ex.timeline(from_day, last).model_copy(update={"crew_id": crew_id})
