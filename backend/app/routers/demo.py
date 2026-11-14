from fastapi import APIRouter, Depends

from .. import examples as ex
from ..deps import CREW, ERRORS, publish, require_roles, roles
from ..schemas import Ok, Packet, RadiationStatus, Rejection, Role, SepStart, User
from ..security import lockout
from . import radiation

router = APIRouter(tags=["12. Demo și simulator"])
E = {k: ERRORS[k] for k in (401, 403, 422)}


@router.post("/sim/sep/start", response_model=RadiationStatus, summary="Pornește furtuna solară", responses=E, openapi_extra=roles(*CREW, Role.earth))
async def sep_start(body: SepStart, user: User = Depends(require_roles(*CREW, Role.earth))):
    """Butonul de demo. Simulatorul redă evenimentul real din DONKI:

    1. rata dozei la dozimetru urcă → la 3 citiri peste 2× media, SHADOW dă alerta de nivel 1 (`radiation.alert`);
    2. avertizarea de pe Pământ pleacă în coadă ca pachet `donki_alert`, direcția `up`, și ajunge după întârzierea legăturii;
    3. la sosire se completează `lead_minutes` în `/radiation/status`.

    **SSE:** `radiation.alert`, `alert.created`, `radiation.reading`, `packet.sent`, apoi `packet.arrived`."""
    radiation.STATE.update(storm=True, sheltered=False)
    ex.DASHBOARD.radiation_alert_active = True
    status = radiation.current()
    publish("radiation.alert", status)
    return status


@router.post("/sim/sep/stop", response_model=RadiationStatus, summary="Oprește furtuna solară", responses=E, openapi_extra=roles(*CREW, Role.earth))
async def sep_stop(user: User = Depends(require_roles(*CREW, Role.earth))):
    """Readuce rata dozei la fond. **SSE:** `radiation.cleared`."""
    radiation.STATE.update(storm=False, sheltered=False)
    ex.DASHBOARD.radiation_alert_active = False
    publish("radiation.cleared", radiation.current())
    return radiation.current()


@router.post("/demo/inject-spoof", response_model=Packet, summary="Injectează un pachet falsificat", responses=E, openapi_extra=roles(*CREW, Role.earth))
async def inject_spoof(user: User = Depends(require_roles(*CREW, Role.earth))):
    """Demo de securitate: pune în coadă un pachet semnat cu o cheie greșită. La sosire e respins și apare cu
    `status = rejected`, `signature_valid = false`, în jurnal și în `/security/rejections`.

    **SSE:** `packet.rejected`."""
    p = ex.PACKETS[2]
    publish("packet.rejected", link_packet(p))
    return link_packet(p)


@router.post("/demo/frozen-sensor", response_model=Rejection, summary="Simulează un senzor înghețat", responses=E, openapi_extra=roles(*CREW, Role.earth))
async def frozen_sensor(user: User = Depends(require_roles(*CREW, Role.earth))):
    """Demo de securitate: simulatorul trimite aceeași valoare de multe ori; stratul de validare o respinge.

    **SSE:** `measurement.rejected`."""
    publish("measurement.rejected", ex.REJECTIONS[1], ex.REJECTIONS[1].crew_id)
    return ex.REJECTIONS[1]


@router.post("/sim/reset", response_model=Ok, summary="Readuce demo-ul la starea inițială", responses=E, openapi_extra=roles(*CREW, Role.earth))
async def reset(user: User = Depends(require_roles(*CREW, Role.earth))):
    """Șterge tot ce s-a schimbat în timpul demo-ului și reîncarcă scenariul: baza se recreează, istoricul se
    regenerează (același seed, deci aceleași date), ceasul repornește la ziua 96, ora 07:00, iar blocările de
    cont se șterg. Durează câteva secunde. Folosiți-l între repetiții.

    După reset, frontend-ul trebuie să reîncarce tot (ca după o reconectare). Tokenurile rămân valabile.

    **SSE:** `mission.tick` cu ziua 96, apoi `dashboard.changed`."""
    radiation.STATE.update(storm=False, sheltered=False)
    ex.DASHBOARD.radiation_alert_active = False
    lockout.reset_all()
    ex.MISSION.mission_day = ex.DAY
    ex.MISSION.sim_now = ex.NOW
    publish("dashboard.changed", {"reason": "reset"})
    return Ok()


def link_packet(p) -> Packet:
    return Packet(**p.model_dump(include=set(Packet.model_fields)))
