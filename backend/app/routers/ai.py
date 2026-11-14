from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..datafiles import DataBundle
from ..db.session import get_session
from ..deps import CREW, ERRORS, current_user, get_app_settings, get_data, require_roles, roles
from ..schemas import AiChatRequest, AiChatResponse, AiStatus, User
from ..services import ai as ai_service

router = APIRouter(prefix="/ai", tags=["10. AI doctor"])


@router.get(
    "/status", response_model=AiStatus, summary="Model status", responses={401: ERRORS[401]}, openapi_extra=roles(*CREW)
)
async def ai_status(user: User = Depends(current_user), settings: Settings = Depends(get_app_settings)):
    """Whether the local model is loaded. When `ready` is `false`, the AI card shows only the catalog text."""
    return await ai_service.status(settings)


@router.post(
    "/chat",
    response_model=AiChatResponse,
    summary="Ask the AI doctor",
    responses={k: ERRORS[k] for k in (401, 403, 422)},
    openapi_extra=roles(*CREW),
)
async def ai_chat(
    body: AiChatRequest,
    user: User = Depends(require_roles(*CREW)),
    session: AsyncSession = Depends(get_session),
    data: DataBundle = Depends(get_data),
    settings: Settings = Depends(get_app_settings),
):
    """A short answer, with NASA sources (RAG), that rephrases the catalog recommendation. **The AI does not decide
    the triage.**

    * It can take 5–15 seconds on a laptop: show a loading state.
    * If the model does not answer within 20 seconds or is off, the endpoint does NOT fail: it returns the catalog
      text, with `fallback = true`. The app works without AI.
    * An astronaut can ask only about their own `crew_id`."""
    return await ai_service.chat(session, data, settings, body, user)
