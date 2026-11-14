"""SHADOW — serviciul AI. Varianta MOCK: răspunde după contract, fără model.

    cd ai && uv run uvicorn service.main:app --port 8001

Echipa de AI înlocuiește corpul funcțiilor (RAG + llama-server), fără să schimbe căile sau modelele.
Backend-ul îl poate folosi din primul minut ca să-și scrie puntea (/ai/chat cu limită de 20 s și fallback).
"""
import time

from fastapi import FastAPI

from .schemas import AiCitation, AiServiceChatRequest, AiServiceChatResponse, AiServiceError, AiServiceStatus

app = FastAPI(title="SHADOW AI service", version="1.2.0",
              description="Contractul dintre backend și serviciul AI. Singurul client: backend-ul.")

OFF_TOPIC = "Pot ajuta doar cu întrebări despre sănătatea ta în misiune."
HEALTH_WORDS = ("puls", "somn", "obosi", "temperat", "tensiun", "inim", "oase", "mușchi", "muschi", "radia",
                "adăpost", "adapost", "alert", "tast", "stres", "febr", "simptom", "exerci", "doz", "ameț")


@app.get("/status", response_model=AiServiceStatus, summary="Starea modelului")
async def status() -> AiServiceStatus:
    return AiServiceStatus(ready=True, model="mock", mode="mock", corpus_documents=0)


@app.post("/chat", response_model=AiServiceChatResponse, summary="Răspuns cu surse",
          responses={503: {"model": AiServiceError, "description": "Modelul nu răspunde (`model_unavailable`). Backend-ul trece pe catalog."}})
async def chat(body: AiServiceChatRequest) -> AiServiceChatResponse:
    """MOCK: reformulează direct recomandarea din context și citează sursa ei.

    Varianta reală: caută 3–4 fragmente în index (întrebare + subiectul alertei), construiește promptul din
    ai/prompts/, cere răspunsul de la llama-server, verifică limitele (fără diagnostic, fără medicamente,
    lungime maximă) și întoarce doar citările folosite."""
    t0 = time.perf_counter()
    rec = body.context.recommendation
    if body.context.topic is None and not any(w in body.message.lower() for w in HEALTH_WORDS):
        return AiServiceChatResponse(answer=OFF_TOPIC, citations=[], off_topic=True, model="mock",
                                     latency_ms=int((time.perf_counter() - t0) * 1000))
    if rec is None:
        answer = "Nu am o recomandare din catalog pentru această întrebare. Dacă te îngrijorează ceva, anunță ofițerul medical."
        cites, ids = [], []
    else:
        evid = "; ".join(e.deviation_text for e in body.context.evidence) or "datele tale s-au abătut de la normalul tău"
        answer = f"Ce s-a observat: {evid}. Ce poți face acum: {rec.action}"
        cites = [AiCitation(title=rec.source_citation, url=rec.source_url, snippet=rec.trigger)]
        ids = [rec.id]
    return AiServiceChatResponse(answer=answer, citations=cites, recommendation_ids=ids, model="mock",
                                 latency_ms=int((time.perf_counter() - t0) * 1000))
