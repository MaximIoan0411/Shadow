import asyncio

from fastapi import APIRouter, Depends

from .. import examples as ex
from ..deps import ALL, ERRORS, ApiError, current_user, roles
from ..schemas import ErrorResponse, LoginAccount, LoginRequest, LoginResponse, Ok, User
from ..security import lockout, passwords
from ..security.errors import AccountLocked

router = APIRouter(prefix="/auth", tags=["1. Autentificare"])

E429 = {429: {"model": ErrorResponse, "description": "Prea multe parole greșite pe acest cont (`too_many_attempts`)."}}

# În mock, parolele de test se trec prin hash la pornire, exact ca în backend-ul real (db/seed.py).
_HASHES = {u: passwords.hash(pw) for u, pw in ex.MOCK_PASSWORDS.items()}


@router.get("/accounts", response_model=list[LoginAccount], summary="Conturile de pe ecranul de autentificare",
            openapi_extra={"x-roles": ["public"]})
async def accounts():
    """Lista conturilor, pentru ecranul „Cine ești?”. **Fără autentificare** și fără nicio dată medicală: doar nume,
    inițiale și rol.

    Frontend: afișați câte o casetă pentru fiecare cont cu `location = "ship"` pe stația de lucru de la bord și
    doar contul cu `location = "earth"` pe ecranul Controlul misiunii. La click pe o casetă cereți parola acelui cont."""
    return ex.ACCOUNTS


@router.post("/login", response_model=LoginResponse, summary="Autentificare (un cont pentru fiecare astronaut)",
             responses={401: ERRORS[401], 422: ERRORS[422], **E429}, openapi_extra={"x-roles": ["public"]})
async def login(body: LoginRequest):
    """**Fiecare astronaut are contul și parola lui.** Nu există cont comun de echipaj: tokenul primit e legat de un
    singur `crew_id`, iar toate datele (baseline, tastare, check-in, alerte) se leagă de el.

    Conturile de test sunt în README, secțiunea 1; parolele de test sunt în fișierul de seed.

    * Parolă greșită → `401 invalid_credentials`. Mesajul e același și dacă utilizatorul nu există.
    * 5 parole greșite pe același cont în 5 minute → `429 too_many_attempts`; contul se deblochează singur după
      60 de secunde reale. `details.retry_after_s` spune cât mai e de așteptat.
    * Fiecare autentificare, reușită sau nu, se scrie în jurnalul de acces (`login` / `login_failed`).

    Frontend: țineți `access_token` în memorie (nu în `localStorage`) și trimiteți-l în antetul
    `Authorization: Bearer <token>`. `user.role` decide ecranul: `astronaut` → corpul interactiv,
    `cmo` → coada ofițerului medical, `earth` → Controlul misiunii."""
    try:
        lockout.check(body.username)
    except AccountLocked as e:
        raise ApiError(429, "too_many_attempts", "Prea multe încercări. Contul e blocat temporar.",
                       {"retry_after_s": e.retry_after_s}) from None
    user = ex.USERS.get(body.username)
    stored = _HASHES.get(body.username, passwords.DUMMY_HASH)          # durează la fel și pentru conturi inexistente
    ok = await asyncio.to_thread(passwords.verify, body.password, stored)  # lent intenționat → în afara buclei async
    if not user or not ok:
        lockout.record_failure(body.username)
        raise ApiError(401, "invalid_credentials", "Utilizator sau parolă greșită.")
    lockout.clear(body.username)
    return LoginResponse(access_token=f"mock-{user.username}", expires_in=43200, user=user)


@router.get("/me", response_model=User, summary="Cine sunt", responses={401: ERRORS[401]}, openapi_extra=roles(*ALL))
async def me(user: User = Depends(current_user)):
    """Întoarce contul din token. Util la reîncărcarea paginii și ca să afișați mereu, vizibil, cine e autentificat."""
    return user


@router.post("/logout", response_model=Ok, summary="Deconectare (schimbarea astronautului)", responses={401: ERRORS[401]}, openapi_extra=roles(*ALL))
async def logout(user: User = Depends(current_user)):
    """Invalidează tokenul curent (backend-ul trece `jti`-ul lui pe lista de tokenuri revocate). Se scrie în jurnal (`logout`).

    **Schimbarea astronautului pe aceeași stație de lucru:** `logout` → ștergeți din memorie tokenul și TOATE datele
    încărcate → închideți conexiunea `/events` → ecranul „Cine ești?” → `login` cu alt cont → deschideți din nou
    `/events`. Colectorul de tastare se oprește la deconectare, ca apăsările să nu ajungă la alt astronaut.

    În mock, tokenul rămâne valid (e textul fix `mock-<utilizator>`)."""
    return Ok()
