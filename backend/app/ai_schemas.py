"""SHADOW — contractul dintre backend și serviciul AI (portul 8001). COPIE a ai/service/schemas.py.

Backend-ul e SINGURUL client al serviciului. Frontend-ul nu-l apelează niciodată direct.
O copie identică a acestui fișier stă în backend/app/ai_schemas.py; scripts/smoke.py oprește orice diferență.
Orice schimbare se face în AMBELE fișiere, în același PR, cu acordul backend-ului.

Reguli:
  * Serviciul NU citește baza de date și nu primește date medicale în afara câmpului `context`.
  * Contextul (alerta, dovezile, recomandarea din catalog) îl construiește backend-ul.
  * Serviciul reformulează recomandarea și citează surse; NU decide nivelul alertei și NU recomandă medicamente.
  * Fallback-ul pe catalog îl face backend-ul (după 20 s sau la o eroare), nu serviciul.
"""
from typing import Literal

from pydantic import BaseModel, Field

Topic = Literal["behavioral", "cardio", "immune", "musculoskeletal", "radiation", "cross_signal"]


class AiEvidence(BaseModel):
    label: str = Field(examples=["Puls de noapte"])
    value: float | None = Field(default=None, examples=[61])
    unit: str = Field(default="", examples=["bpm"])
    deviation_text: str = Field(examples=["+7 bpm peste mediana personală, 3 nopți"])


class AiRecommendation(BaseModel):
    """Intrarea din catalog pe care răspunsul trebuie s-o reformuleze."""
    id: str = Field(examples=["immune-2-1"])
    level: Literal[1, 2, 3]
    trigger: str
    action: str
    source_citation: str
    source_url: str


class AiContext(BaseModel):
    """Construit de backend. Fără nume, fără crew_id: serviciul nu are nevoie să știe cine întreabă."""
    topic: Topic | None = Field(default=None, description="Subiectul alertei. `null` = întrebare generală.")
    level: Literal[1, 2, 3] | None = None
    alert_title: str | None = Field(default=None, examples=["Puls de noapte +7 bpm, 3 nopți la rând"])
    evidence: list[AiEvidence] = Field(default_factory=list)
    recommendation: AiRecommendation | None = None
    mission_day: int = Field(examples=[96])
    environment: str = Field(examples=["mars_transit"])


class AiTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class AiServiceChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000, examples=["De ce mi-a crescut pulsul de noapte?"])
    history: list[AiTurn] = Field(default_factory=list, max_length=6)
    context: AiContext


class AiCitation(BaseModel):
    title: str = Field(examples=["Alavi et al. (2022), Nature Medicine"])
    url: str
    snippet: str = Field(description="Fragmentul din corpus folosit efectiv în răspuns.")


class AiServiceChatResponse(BaseModel):
    answer: str = Field(description="În română, 3–5 propoziții.")
    citations: list[AiCitation] = Field(description="Doar fragmentele folosite. Gol = fără sursă.")
    recommendation_ids: list[str] = Field(default_factory=list, examples=[["immune-2-1"]])
    off_topic: bool = Field(default=False, description="True = întrebarea nu ține de sănătatea în misiune; `answer` e mesajul fix.")
    model: str = Field(examples=["model-3b-Q4_K_M"])
    latency_ms: int


class AiServiceStatus(BaseModel):
    ready: bool = Field(description="False = modelul nu e încărcat; backend-ul trece direct pe catalog.")
    model: str | None = None
    mode: Literal["local", "colab_simulation", "mock"] = Field(description="Unde rulează modelul. Frontend-ul îl afișează onest.")
    corpus_documents: int = Field(default=0, description="Câte documente sunt în index.")


class AiServiceError(BaseModel):
    """Corpul răspunsurilor 503 (modelul nu răspunde) și 422 (cerere invalidă)."""
    error: dict = Field(examples=[{"code": "model_unavailable", "message": "llama-server nu răspunde."}])
