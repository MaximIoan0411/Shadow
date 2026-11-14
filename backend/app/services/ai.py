import logging
import time

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai_schemas import (
    AiContext,
    AiEvidence,
    AiRecommendation,
    AiServiceChatRequest,
    AiServiceChatResponse,
    AiServiceStatus,
)
from ..clock import clock
from ..config import Settings
from ..datafiles import DataBundle
from ..deps import ApiError
from ..schemas import AiChatRequest, AiChatResponse, AiStatus, Citation, Role, User
from . import alerts as alerts_service
from . import mission as mission_service

log = logging.getLogger(__name__)

DISCLAIMER = "Decision-support prototype, not a medical device."
GENERAL_ANSWER = (
    "I can help with questions about your health data in the mission. Ask about one of your alerts to get the "
    "recommendation from the NASA-based catalog."
)
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


def _fallback(entries: list, started: float) -> AiChatResponse:
    latency = int((time.perf_counter() - started) * 1000)
    if not entries:
        return AiChatResponse(
            answer=GENERAL_ANSWER,
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
        return _fallback(entries, started)
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
