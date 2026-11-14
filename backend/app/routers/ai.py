from fastapi import APIRouter, Depends

from .. import examples as ex
from ..deps import CREW, ERRORS, ApiError, current_user, require_roles, roles
from ..schemas import AiChatRequest, AiChatResponse, AiStatus, Role, User

router = APIRouter(prefix="/ai", tags=["10. Medicul AI"])


@router.get("/status", response_model=AiStatus, summary="Starea modelului", responses={401: ERRORS[401]}, openapi_extra=roles(*CREW))
async def ai_status(user: User = Depends(current_user)):
    """Dacă modelul local e încărcat. Când `ready` e `false`, cardul AI afișează doar textul din catalog."""
    return AiStatus(ready=True, model="mock", mode="mock")


@router.post("/chat", response_model=AiChatResponse, summary="Întreabă medicul AI", responses={k: ERRORS[k] for k in (401, 403, 422)}, openapi_extra=roles(*CREW))
async def ai_chat(body: AiChatRequest, user: User = Depends(require_roles(*CREW))):
    """Răspuns scurt, cu surse NASA (RAG), care reformulează recomandarea din catalog. **AI-ul nu decide triajul.**

    * Poate dura 5–15 secunde pe laptop: afișați o stare de încărcare.
    * Dacă modelul nu răspunde în 20 de secunde sau e oprit, endpoint-ul NU dă eroare: întoarce textul din catalog,
      cu `fallback = true`. Aplicația merge și fără AI.
    * Astronautul poate întreba doar despre propriul `crew_id`."""
    if user.role == Role.astronaut and body.crew_id != user.crew_id:
        raise ApiError(403, "forbidden", "Poți întreba doar despre datele tale.")
    return ex.AI_ANSWER
