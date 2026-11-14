from fastapi import APIRouter, Depends

from .. import examples as ex
from ..deps import ALL, CREW, ERRORS, ApiError, current_user, publish, require_roles, roles
from ..schemas import ClockUpdate, EnvironmentInfo, EnvironmentUpdate, MissionState, User

router = APIRouter(tags=["2. Misiune, mediu, ceas"])


@router.get("/mission", response_model=MissionState, summary="Starea misiunii", responses={401: ERRORS[401]}, openapi_extra=roles(*ALL))
async def get_mission(user: User = Depends(current_user)):
    """Ora misiunii (SimClock), ziua curentă, mediul și starea legăturii cu Pământul.

    Misiunea pornește în **ziua 96, ora 07:00** (zilele 1–95 sunt istoric generat la pornirea serverului), cu
    timpul accelerat de `time_scale` ori (implicit ×60: o zi de misiune = 24 de minute reale).

    Apelați-l o dată la pornire. După aceea, ora vine prin SSE (`mission.tick`), nu prin polling."""
    return ex.MISSION


@router.get("/environments", response_model=list[EnvironmentInfo], summary="Lista mediilor", responses={401: ERRORS[401]}, openapi_extra=roles(*ALL))
async def list_environments(user: User = Depends(current_user)):
    """Cele 4 medii pentru comutator: stație, Lună, tranzit spre Marte, bază pe Marte."""
    return ex.ENVIRONMENTS


@router.put("/mission/environment", response_model=MissionState, summary="Schimbă mediul",
            responses={k: ERRORS[k] for k in (401, 403, 422)}, openapi_extra=roles(*CREW))
async def set_environment(body: EnvironmentUpdate, user: User = Depends(require_roles(*CREW))):
    """Comutatorul de mediu. Schimbă întârzierea legăturii, rata de doză de fond și pragurile dependente de gravitație.

    **Efecte:** pachetele deja `in_transit` își păstrează ora de sosire; cele noi folosesc noua întârziere.
    **SSE:** `environment.changed` cu noul `MissionState`."""
    env = ex.ENV_BY_ID[body.environment]
    scale = ex.MISSION.time_scale
    ex.MISSION.environment = env
    ex.MISSION.link.environment = env.id
    ex.MISSION.link.one_way_delay_s = env.one_way_delay_s
    ex.MISSION.link.one_way_delay_real_s = round(env.one_way_delay_s / scale, 2)
    publish("environment.changed", ex.MISSION)
    return ex.MISSION


@router.put("/sim/clock", response_model=MissionState, summary="Schimbă viteza sau ziua ceasului (demo)",
            responses={k: ERRORS[k] for k in (401, 403, 409, 422)}, openapi_extra=roles(*CREW))
async def set_clock(body: ClockUpdate, user: User = Depends(require_roles(*CREW))):
    """Doar pentru demo.

    * `time_scale` schimbă viteza; ora curentă a misiunii rămâne aceeași.
    * `mission_day` sare **înainte** la începutul acelei zile (07:00): backend-ul generează zilele lipsă cu
      simulatorul și rulează motorul peste ele, deci pot apărea alerte noi. **Înapoi nu se poate** (409
      `invalid_state`); pentru o repetiție de la capăt folosiți `POST /sim/reset`.

    Derulatorul NU folosește acest endpoint: el doar citește istoricul cu `?as_of_day=`.

    **SSE:** `mission.tick` cu noua zi, apoi `dashboard.changed` și eventual `alert.created`."""
    if body.mission_day is not None and body.mission_day < ex.MISSION.mission_day:
        raise ApiError(409, "invalid_state", f"Ceasul nu poate merge înapoi (ziua curentă: {ex.MISSION.mission_day}). Folosiți /sim/reset.")
    if body.mission_day is not None and body.mission_day > ex.MISSION.total_days:
        raise ApiError(422, "validation_error", f"Misiunea are {ex.MISSION.total_days} de zile.",
                       {"fields": [{"field": "mission_day", "problem": "după sfârșitul misiunii"}]})
    if body.time_scale is not None:
        ex.MISSION.time_scale = body.time_scale
        ex.MISSION.link.one_way_delay_real_s = round(ex.MISSION.link.one_way_delay_s / body.time_scale, 2)
    if body.mission_day is not None:
        ex.MISSION.mission_day = body.mission_day
        ex.MISSION.sim_now = ex.d(body.mission_day, 7, 0)
    return ex.MISSION
