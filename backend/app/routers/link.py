
from fastapi import APIRouter, Depends, Query

from .. import examples as ex
from ..deps import ALL, CREW, ERRORS, ApiError, crew_access, current_user, publish, require_roles, roles
from ..schemas import (
    CrewMessage,
    EarthReplyCreate,
    LinkStatus,
    OutboxCreate,
    Packet,
    PacketDetail,
    PacketDirection,
    PacketKind,
    PacketStatus,
    Role,
    User,
)

router = APIRouter(tags=["8. Legătura cu Pământul"])
E = {k: ERRORS[k] for k in (401, 403, 404, 422)}


def _packet(p: PacketDetail) -> Packet:
    return Packet(**p.model_dump(include=set(Packet.model_fields)))


@router.get("/link/status", response_model=LinkStatus, summary="Starea legăturii", responses={401: ERRORS[401]}, openapi_extra=roles(*ALL))
async def link_status(user: User = Depends(current_user)):
    """Întârzierea curentă, dacă fereastra e deschisă și câte pachete așteaptă în fiecare sens."""
    return ex.MISSION.link


@router.get("/link/packets", response_model=list[Packet], summary="Coada de pachete", responses={k: ERRORS[k] for k in (401, 403)}, openapi_extra=roles(Role.cmo, Role.earth))
async def list_packets(direction: PacketDirection | None = None, status: PacketStatus | None = None,
                 limit: int = Query(default=50, ge=1, le=200), user: User = Depends(require_roles(Role.cmo, Role.earth))):
    """Plicurile pachetelor, cele mai noi primele — tabelul din ecranul „Controlul misiunii”.

    Câmpul `progress` e calculat la momentul răspunsului. Pentru o bară fluidă, animați local folosind
    `eta_real_s` și reîncărcați lista doar la SSE `packet.sent` / `packet.arrived` / `packet.rejected`."""
    out = [_packet(p) for p in ex.PACKETS if (direction is None or p.direction == direction) and (status is None or p.status == status)]
    return out[:limit]


@router.get("/link/packets/{packet_id}", response_model=PacketDetail, summary="Un pachet, cu conținutul decriptat", responses=E, openapi_extra=roles(Role.cmo, Role.earth))
async def get_packet(packet_id: str, user: User = Depends(require_roles(Role.cmo, Role.earth))):
    """`payload` apare doar pentru pachetele `delivered`. Rolul `earth` vede conținutul pachetelor `down` ajunse;
    rolul `cmo` vede conținutul pachetelor `up` ajunse și al celor trimise de el. Altfel `payload` e `null`."""
    p = ex.PACKET_BY_ID.get(packet_id)
    if not p:
        raise ApiError(404, "not_found", f"Nu există pachetul {packet_id}.")
    return p


@router.post("/link/outbox", response_model=Packet, status_code=201, summary="Pune un mesaj în coada spre Pământ", responses=E, openapi_extra=roles(*CREW))
async def create_outbox(body: OutboxCreate, user: User = Depends(require_roles(*CREW))):
    """Pentru rezumatul săptămânal aprobat de astronaut (`weekly_summary`). Alertele de nivel 3 intră în coadă automat,
    prin `/alerts/{id}/escalate`; folosiți `alert_l3` aici doar pentru retrimitere.

    Astronautul poate trimite doar despre propriul `crew_id`. Pachetul pornește `queued` și pleacă la următoarea
    fereastră de comunicare.

    **SSE:** `packet.sent` când pleacă, `packet.arrived` când ajunge."""
    if user.role == Role.astronaut and body.crew_id != user.crew_id:
        raise ApiError(403, "forbidden", "Poți trimite doar date despre tine.")
    if body.kind == "alert_l3" and not body.alert_id:
        raise ApiError(422, "validation_error", "Pentru alert_l3 trebuie alert_id.", {"field": "alert_id"})
    p = Packet(id="pk-0008", seq=8, direction=PacketDirection.down, kind=PacketKind(body.kind), status=PacketStatus.queued,
               title="Rezumat săptămânal aprobat de astronaut" if body.kind == "weekly_summary" else "Alertă de nivel 3",
               sender=user.display_name, crew_id=body.crew_id, alert_id=body.alert_id, created_at=ex.MISSION.sim_now,
               progress=0, signature_valid=None, size_bytes=2048)
    return p


@router.post("/earth/replies", response_model=Packet, status_code=201, summary="Răspunsul medicului de pe Pământ", responses=E, openapi_extra=roles(Role.earth))
async def earth_reply(body: EarthReplyCreate, user: User = Depends(require_roles(Role.earth))):
    """Butonul „Pune în coadă, criptat” din Controlul misiunii. Răspunsul pleacă la următoarea fereastră și ajunge la
    bord după `one_way_delay_s`. Când ajunge, apare în `/crew/{id}/messages` și în `earth_reply` al alertei.

    **SSE:** `packet.sent`, apoi `packet.arrived` (cu `crew_id`) la sosire."""
    p = Packet(id="pk-0009", seq=9, direction=PacketDirection.up, kind=PacketKind.earth_reply, status=PacketStatus.queued,
               title="Răspuns: " + body.body[:60], sender=user.display_name, crew_id=body.crew_id, alert_id=body.alert_id,
               in_reply_to=body.in_reply_to, created_at=ex.MISSION.sim_now, progress=0, size_bytes=len(body.body.encode()) + 512)
    publish("packet.sent", p)
    return p


@router.get("/crew/{crew_id}/messages", response_model=list[CrewMessage], summary="Mesaje sosite de pe Pământ", responses=E, openapi_extra=roles(*CREW))
async def crew_messages(crew_id: str, user: User = Depends(crew_access)):
    """Răspunsurile medicului de zbor și avertizările DONKI care AU AJUNS la bord, deja decriptate și verificate.
    Cele încă pe drum nu apar aici."""
    return ex.MESSAGES if crew_id == "cm-2" else []
