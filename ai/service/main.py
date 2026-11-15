"""SHADOW — serviciul AI (medicul de bord). Singurul client: backend-ul.

    cd ai && uv run uvicorn service.main:app --port 8001

Pentru o întrebare: caută 3–4 fragmente în baza de cunoștințe (rag/), construiește promptul (prompts/), cere
răspunsul de la llama-server (local sau pe Colab, prin tunel; vezi colab/), verifică regulile (guard.py) și
întoarce doar citările folosite. Fără `SHADOW_LLM_URL` rulează ca mock: reformulează recomandarea din catalog.
Dacă modelul nu răspunde, întoarce repede 503 `model_unavailable`; fallback-ul pe catalog îl face backend-ul.
"""
import logging
import time
from contextlib import asynccontextmanager

import anyio
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from rag.retrieve import Passage, index_ready, load_index, retrieve

from . import guard
from .config import load_settings
from .llm import LlmClient, LlmUnavailable
from .prompting import build_messages
from .schemas import AiServiceChatRequest, AiServiceChatResponse, AiServiceError, AiServiceStatus

log = logging.getLogger("shadow.ai")

CATALOG_MODEL = "catalog"
"""Numele de model întors când răspunsul modelului a fost respins de gardă și s-a afișat textul din catalog."""
SETTINGS = load_settings()
STATE: dict = {"llm": None}


def warm_index() -> None:
    """Încarcă indexul și modelul de embedding la pornire, ca prima întrebare din demo să nu fie cea lentă."""
    if not index_ready():
        log.warning("Indexul lipsește: rulați `uv run python -m rag.ingest`. Medicul AI răspunde fără surse.")
        return
    load_index()
    retrieve("warm up", None)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await anyio.to_thread.run_sync(warm_index)
    if SETTINGS.llm_url:
        client = LlmClient(SETTINGS)
        STATE["llm"] = client
        name = await client.model()
        log.warning("Model %s la %s (%s)", name or "INDISPONIBIL", SETTINGS.llm_url, SETTINGS.mode)
    yield
    if STATE["llm"]:
        await STATE["llm"].close()


app = FastAPI(title="SHADOW AI service", version="1.2.0", lifespan=lifespan,
              description="Contractul dintre backend și serviciul AI. Singurul client: backend-ul.")


def ms_since(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def unavailable(message: str) -> JSONResponse:
    return JSONResponse(status_code=503, content={"error": {"code": "model_unavailable", "message": message}})


@app.get("/status", response_model=AiServiceStatus, summary="Starea modelului")
async def status() -> AiServiceStatus:
    documents = load_index().documents if index_ready() else 0
    client: LlmClient | None = STATE["llm"]
    if client is None:
        return AiServiceStatus(ready=True, model="mock", mode="mock", corpus_documents=documents)
    name = await client.model()
    return AiServiceStatus(ready=name is not None, model=name, mode=SETTINGS.mode, corpus_documents=documents)


@app.post("/chat", response_model=AiServiceChatResponse, summary="Răspuns cu surse",
          responses={503: {"model": AiServiceError, "description": "Modelul nu răspunde (`model_unavailable`). Backend-ul trece pe catalog."}})
async def chat(body: AiServiceChatRequest):
    started = time.perf_counter()
    context = body.context
    rec = context.recommendation
    hint = " ".join(part for part in (context.alert_title, rec.trigger if rec else None) if part)
    passages: list[Passage] = await anyio.to_thread.run_sync(retrieve, body.message, context.topic, hint) if index_ready() else []
    client: LlmClient | None = STATE["llm"]
    model = client.model_name if client and client.model_name else "mock"

    if guard.looks_off_topic(body.message, context.topic, passages):
        return AiServiceChatResponse(answer=guard.OFF_TOPIC, citations=[], off_topic=True, model=model, latency_ms=ms_since(started))

    evidence = [item.deviation_text for item in context.evidence]
    if client is None:
        # mock: reformularea fixă a recomandării (sau fraza din sursă), cu sursa ei
        answer, citations = guard.fallback(rec, evidence, passages, body.message, context.open_alerts)
        return AiServiceChatResponse(answer=answer, citations=citations, recommendation_ids=[rec.id] if rec else [],
                                     model="mock", latency_ms=ms_since(started))

    try:
        raw = await client.complete(build_messages(body, passages))
    except LlmUnavailable as error:
        log.warning("Modelul nu răspunde: %s", error)
        return unavailable("Modelul nu răspunde.")
    if not raw:
        return unavailable("Modelul a întors un răspuns gol.")

    answered_by = client.model_name or model
    if guard.hides_open_alert(raw, context.open_alerts):
        log.warning("Răspuns respins (spune că totul e în regulă, cu o alertă deschisă): %s", raw[:200])
        return AiServiceChatResponse(answer=guard.open_alerts_answer(context.open_alerts), citations=[],
                                     recommendation_ids=[a.recommendation_id for a in context.open_alerts[:1]],
                                     model=CATALOG_MODEL, latency_ms=ms_since(started))
    if guard.violates_rules(raw):
        log.warning("Răspuns respins (medicament, doză, diagnostic sau raționament scăpat): %s", raw[:200])
        answer, citations = guard.fallback(rec, evidence, passages, body.message, context.open_alerts)
        answered_by = CATALOG_MODEL  # textul afișat e al catalogului, nu al modelului: se spune deschis
    else:
        answer, citations = guard.attach_citations(guard.clip(raw), passages, rec)
    return AiServiceChatResponse(answer=answer, citations=citations, recommendation_ids=[rec.id] if rec else [],
                                 model=answered_by, latency_ms=ms_since(started))
