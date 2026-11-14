from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..datafiles import DataBundle
from ..db.session import get_session
from ..deps import ALL, CREW, ERRORS, crew_access, current_user, get_data, require_roles, roles
from ..schemas import (
    CrewMessage,
    EarthReplyCreate,
    LinkStatus,
    OutboxCreate,
    Packet,
    PacketDetail,
    PacketDirection,
    PacketStatus,
    Role,
    User,
)
from ..services import link as link_service
from ..services import mission as mission_service

router = APIRouter(tags=["8. Link with Earth"])
E = {k: ERRORS[k] for k in (401, 403, 404, 422)}


@router.get(
    "/link/status",
    response_model=LinkStatus,
    summary="Link status",
    responses={401: ERRORS[401]},
    openapi_extra=roles(*ALL),
)
async def link_status(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """The current delay, whether the window is open and how many packets wait in each direction."""
    return (await mission_service.state(session, data)).link


@router.get(
    "/link/packets",
    response_model=list[Packet],
    summary="Packet queue",
    responses={k: ERRORS[k] for k in (401, 403)},
    openapi_extra=roles(Role.cmo, Role.earth),
)
async def list_packets(
    direction: PacketDirection | None = None,
    status: PacketStatus | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(require_roles(Role.cmo, Role.earth)),
    session: AsyncSession = Depends(get_session),
):
    """The packet envelopes, newest first — the table on the "Mission Control" screen.

    The `progress` field is computed at response time. For a smooth bar, animate locally using `eta_real_s` and
    reload the list only on SSE `packet.sent` / `packet.arrived` / `packet.rejected`."""
    return await link_service.packets(session, direction, status, limit)


@router.get(
    "/link/packets/{packet_id}",
    response_model=PacketDetail,
    summary="One packet, with the decrypted content",
    responses=E,
    openapi_extra=roles(Role.cmo, Role.earth),
)
async def get_packet(
    packet_id: str,
    user: User = Depends(require_roles(Role.cmo, Role.earth)),
    session: AsyncSession = Depends(get_session),
):
    """`payload` appears only for `delivered` packets. The `earth` role sees the content of `down` packets that
    arrived; the `cmo` role sees the content of `up` packets that arrived and of the ones they sent. Otherwise
    `payload` is `null`."""
    return await link_service.packet(session, packet_id, user)


@router.post(
    "/link/outbox",
    response_model=Packet,
    status_code=201,
    summary="Put a message in the queue to Earth",
    responses={**E, 409: ERRORS[409]},
    openapi_extra=roles(*CREW),
)
async def create_outbox(
    body: OutboxCreate,
    user: User = Depends(require_roles(*CREW)),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
):
    """For the weekly summary approved by the astronaut (`weekly_summary`). An astronaut can send only about
    their own `crew_id`.

    Level 3 alerts enter the queue automatically, through `/alerts/{id}/escalate`. `alert_l3` here only sends one
    **again**: crew medical officer only (`403` otherwise), and only for an alert already at level 3 (`409`
    otherwise).

    The packet starts `queued` and leaves at the next communication window.

    **SSE:** `packet.sent` when it leaves, `packet.arrived` when it arrives."""
    return await link_service.outbox(session, data, body, user)


@router.post(
    "/earth/replies",
    response_model=Packet,
    status_code=201,
    summary="The reply of the flight surgeon on Earth",
    responses=E,
    openapi_extra=roles(Role.earth),
)
async def earth_reply(
    body: EarthReplyCreate,
    user: User = Depends(require_roles(Role.earth)),
    session: AsyncSession = Depends(get_session),
):
    """The "Queue, encrypted" button on Mission Control. The reply leaves at the next window and reaches the ship
    after `one_way_delay_s`. When it arrives, it shows up in `/crew/{id}/messages` and in the alert's `earth_reply`.

    **SSE:** `packet.sent`, then `packet.arrived` (with `crew_id`) on arrival."""
    return await link_service.earth_reply(session, body, user)


@router.get(
    "/crew/{crew_id}/messages",
    response_model=list[CrewMessage],
    summary="Messages arrived from Earth",
    responses=E,
    openapi_extra=roles(*CREW),
)
async def crew_messages(crew_id: str, user: User = Depends(crew_access), session: AsyncSession = Depends(get_session)):
    """The flight surgeon's replies and the DONKI warnings that HAVE ARRIVED on board, already decrypted and
    verified. The ones still on their way do not appear here."""
    return await link_service.messages(session, crew_id)
