from fastapi import APIRouter, Depends, Query

from .. import examples as ex
from ..deps import CREW, ERRORS, crew_access, roles
from ..schemas import KeystrokeBatch, KeystrokeResult, KeystrokeSummary, PvtResult, PvtSubmit, Status, User

router = APIRouter(tags=["5. Tastare și test de reacție"])
E = {k: ERRORS[k] for k in (401, 403, 404, 422)}


@router.post("/crew/{crew_id}/keystrokes/batches", response_model=KeystrokeResult, summary="Trimite un lot de apăsări de taste", responses=E, openapi_extra=roles(*CREW))
async def post_keystrokes(crew_id: str, body: KeystrokeBatch, user: User = Depends(crew_access)):
    """**Confidențialitate: trimiteți doar timpii și clasa tastei, niciodată caracterul.** Backend-ul respinge cu 422
    orice câmp în plus (ex. `key`, `code`, `text`).

    Frontend: adunați evenimentele `keydown`/`keyup` și trimiteți un lot la ~5 secunde sau la 200 de taste, cu
    același `session_id` cât timp utilizatorul scrie în același câmp. Răspunsul conține trăsăturile cumulate ale
    sesiunii, deci îl puteți afișa direct în barele live.

    Primele sesiuni construiesc baseline-ul: cât timp `baseline_ready` e `false`, `status` e `unknown`.

    **SSE:** `alert.created` dacă abaterea trece pragul."""
    return KeystrokeResult(session_id=body.session_id, features=ex.KS_NOW.model_copy(update={"n_keys": len(body.events)}), baseline=ex.KS_BASE,
                           deviation_z={"hold_ms_mean": 1.9, "flight_ms_mean": 1.5, "keys_per_min": -1.6, "backspace_rate": 0.3},
                           fatigue_index=68, status=Status.watch, baseline_ready=True, baseline_sessions=9)


@router.get("/crew/{crew_id}/keystrokes/summary", response_model=KeystrokeSummary, summary="Rezumatul tastării", responses=E, openapi_extra=roles(*CREW))
async def keystroke_summary(crew_id: str, last: int = Query(default=10, ge=1, le=100, description="Câte sesiuni recente să întoarcă."), user: User = Depends(crew_access)):
    """Baseline-ul personal, ultima sesiune și sesiunile recente. Pentru cardul „Ritmul tău” și pentru comparația din demo."""
    return ex.KS_SUMMARY


@router.post("/crew/{crew_id}/pvt", response_model=PvtResult, status_code=201, summary="Trimite un test de reacție (PVT-B)", responses=E, openapi_extra=roles(*CREW))
async def post_pvt(crew_id: str, body: PvtSubmit, user: User = Depends(crew_access)):
    """Testul de 3 minute rulează integral în frontend; aici trimiteți toate încercările la sfârșit.

    Backend-ul calculează media 1/RT, lapsusurile (RT ≥ 355 ms) și abaterea față de baseline. Primele 2–3 teste
    sunt de antrenament și nu intră în baseline.

    **SSE:** `dashboard.changed`."""
    return ex.PVT.model_copy(update={"crew_id": crew_id})


@router.get("/crew/{crew_id}/pvt", response_model=list[PvtResult], summary="Istoricul testelor de reacție", responses=E, openapi_extra=roles(*CREW))
async def list_pvt(crew_id: str, limit: int = Query(default=20, ge=1, le=200), user: User = Depends(crew_access)):
    return [ex.PVT.model_copy(update={"crew_id": crew_id})]
