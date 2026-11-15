import logging
import time

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai_schemas import (
    AiContext,
    AiEvidence,
    AiOpenAlert,
    AiRecommendation,
    AiServiceChatRequest,
    AiServiceChatResponse,
    AiServiceStatus,
    AiZone,
)
from ..clock import clock
from ..config import Settings
from ..datafiles import DataBundle
from ..db.models.alerts import Alert as AlertRow
from ..deps import ApiError
from ..schemas import AiChatRequest, AiChatResponse, AiStatus, Citation, Role, User
from . import alerts as alerts_service
from . import crew as crew_service
from . import mission as mission_service

log = logging.getLogger(__name__)

DISCLAIMER = "Decision-support prototype, not a medical device."
GENERAL_ANSWER = (
    "I can help with questions about your health data in the mission. Ask about one of your alerts to get the "
    "recommendation from the NASA-based catalog."
)
MAX_OPEN_ALERTS = 5
MAX_OBSERVED = 3
CMO_MIN_LEVEL = 2
STATUS_TIMEOUT_S = 3.0
CATALOG_MODEL = "catalog"
"""The model name when the text shown is the catalog's: our own fallback, or the AI service after its guard
rejected the model's answer (a medicine, a dose, a diagnosis)."""

# httpx transport used for the AI service; tests replace it with httpx.MockTransport
transport: httpx.AsyncBaseTransport | None = None


async def build_context(
    session: AsyncSession, data: DataBundle, body: AiChatRequest, user: User
) -> tuple[AiContext, list]:
    """The context for the AI service: the alert, its evidence and the catalog recommendation, the mission day and
    the environment. No name and no crew_id. Also returns the catalog entries for the fallback."""
    context = AiContext(
        mission_day=clock.mission_day(), environment=await mission_service.current_environment_id(session, data)
    )
    if body.alert_id is None:
        # a general question: the model still has to know how this astronaut is doing, or it answers as if there
        # were no data. It gets the open alerts (with what the catalog says to do) and the four body zones.
        context.open_alerts = await _open_alerts(session, data, body.crew_id, user)
        dashboard = await crew_service.dashboard(session, data, body.crew_id, None)
        context.zones = [AiZone(name=p.name, status=p.status.value, headline=p.headline) for p in dashboard.pillars]
        return context, []
    alert = await alerts_service.get_row(session, body.alert_id, user)
    if alert.crew_id != body.crew_id:
        raise ApiError(422, "validation_error", "The alert belongs to another crew member.")
    entry = data.catalog.by_id()[alert.recommendation_id]
    context.topic = alert.topic
    context.level = alert.level
    context.alert_title = alert.title
    context.evidence = [
        AiEvidence(label=e["label"], value=e.get("value"), unit=e.get("unit", ""), deviation_text=e["deviation_text"])
        for e in alert.evidence
    ]
    context.recommendation = AiRecommendation(
        id=entry.id,
        level=entry.level,
        trigger=entry.trigger,
        action=entry.action,
        source_citation=entry.source.citation,
        source_url=entry.source.url,
    )
    return context, [entry]


async def _open_alerts(session: AsyncSession, data: DataBundle, crew_id: str, user: User) -> list[AiOpenAlert]:
    """The member's unresolved alerts, most serious first, with the same visibility as GET /crew/{id}/alerts: the
    crew medical officer sees a colleague's alerts from level 2 up."""
    stmt = select(AlertRow).where(AlertRow.crew_id == crew_id, AlertRow.state != "resolved")
    if user.role == Role.cmo and user.crew_id != crew_id:
        stmt = stmt.where(AlertRow.level >= CMO_MIN_LEVEL)
    rows = sorted((await session.scalars(stmt)).all(), key=lambda a: (-a.level, a.created_at))[:MAX_OPEN_ALERTS]
    catalog = data.catalog.by_id()
    return [
        AiOpenAlert(
            topic=a.topic,
            level=a.level,
            title=a.title,
            observed=[e["deviation_text"] for e in a.evidence][:MAX_OBSERVED],
            recommendation_id=a.recommendation_id,
            action=catalog[a.recommendation_id].action,
        )
        for a in rows
    ]


def general_answer(open_alerts: list[AiOpenAlert]) -> str:
    """The catalog's answer to a general question when the model is not there: it names the open alerts instead
    of pretending there is nothing to say."""
    if not open_alerts:
        return "You have no open alerts: all your zones are within your own normal. " + GENERAL_ANSWER
    names = "; ".join(f"{a.title} (level {a.level})" for a in open_alerts)
    count = f"{len(open_alerts)} open alert{'s' if len(open_alerts) > 1 else ''}"
    return f"You have {count}: {names}. Open an alert to see what the NASA-based catalog says to do."


def _fallback(entries: list, started: float, open_alerts: list[AiOpenAlert]) -> AiChatResponse:
    latency = int((time.perf_counter() - started) * 1000)
    if not entries:
        return AiChatResponse(
            answer=general_answer(open_alerts),
            citations=[],
            recommendation_ids=[],
            model=CATALOG_MODEL,
            latency_ms=latency,
            fallback=True,
            disclaimer=DISCLAIMER,
        )
    entry = entries[0]
    return AiChatResponse(
        answer=entry.action,
        citations=[Citation(title=entry.source.citation, url=entry.source.url, snippet=entry.trigger)],
        recommendation_ids=[entry.id],
        model=CATALOG_MODEL,
        latency_ms=latency,
        fallback=True,
        disclaimer=DISCLAIMER,
    )


async def chat(
    session: AsyncSession, data: DataBundle, settings: Settings, body: AiChatRequest, user: User
) -> AiChatResponse:
    if user.role == Role.astronaut and body.crew_id != user.crew_id:
        raise ApiError(403, "forbidden", "You can only ask about your own data.")
    context, entries = await build_context(session, data, body, user)
    # the database session is closed before waiting for the model (it can take up to 20 s)
    await session.close()

    request = AiServiceChatRequest(
        message=body.message,
        history=[{"role": m.role, "content": m.content} for m in body.history[-6:]],
        context=context,
    )
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=settings.ai_timeout_s, transport=transport) as client:
            r = await client.post(f"{settings.ai_url}/chat", json=request.model_dump(mode="json"))
            r.raise_for_status()
            answer = AiServiceChatResponse.model_validate(r.json())
    except Exception as e:  # timeout, connection refused, 503, 422, invalid body: never an error for the user
        log.warning("AI service unavailable, answering from the catalog: %s", type(e).__name__)
        return _fallback(entries, started, context.open_alerts)
    return AiChatResponse(
        answer=answer.answer,
        citations=[Citation(title=c.title, url=c.url, snippet=c.snippet) for c in answer.citations],
        recommendation_ids=answer.recommendation_ids,
        model=answer.model,
        latency_ms=int((time.perf_counter() - started) * 1000),
        fallback=answer.model == CATALOG_MODEL,
        disclaimer=DISCLAIMER,
    )


async def status(settings: Settings) -> AiStatus:
    try:
        async with httpx.AsyncClient(
            timeout=min(settings.ai_timeout_s, STATUS_TIMEOUT_S), transport=transport
        ) as client:
            r = await client.get(f"{settings.ai_url}/status")
            r.raise_for_status()
            s = AiServiceStatus.model_validate(r.json())
    except Exception:
        return AiStatus(ready=False, model=None, mode="fallback")
    if not s.ready:
        return AiStatus(ready=False, model=s.model, mode="fallback")
    return AiStatus(ready=True, model=s.model, mode=s.mode)
