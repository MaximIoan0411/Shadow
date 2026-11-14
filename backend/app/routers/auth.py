from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..db.session import get_session
from ..deps import ALL, ERRORS, current_user, get_app_settings, roles
from ..schemas import ErrorResponse, LoginAccount, LoginRequest, LoginResponse, Ok, User
from ..services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["1. Authentication"])

E429 = {429: {"model": ErrorResponse, "description": "Too many wrong passwords on this account (`too_many_attempts`)."}}


@router.get(
    "/accounts",
    response_model=list[LoginAccount],
    summary="Accounts shown on the sign-in screen",
    openapi_extra={"x-roles": ["public"]},
)
async def accounts(session: AsyncSession = Depends(get_session)):
    """The list of accounts for the "Who are you?" screen. **No authentication** and no medical data at all: only
    names, initials and role.

    Frontend: show one tile per account with `location = "ship"` on the onboard workstation and only the account
    with `location = "earth"` on the Mission Control screen. On click, ask for that account's password."""
    return await auth_service.list_accounts(session)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Sign in (one account per astronaut)",
    responses={401: ERRORS[401], 422: ERRORS[422], **E429},
    openapi_extra={"x-roles": ["public"]},
)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
):
    """**Every astronaut has their own account and password.** There is no shared crew account: the token is bound
    to a single `crew_id`, and all data (baseline, typing, check-in, alerts) is linked to it.

    Test accounts are in the README, section 1; test passwords are in the seed file.

    * Wrong password → `401 invalid_credentials`. The message is the same when the user does not exist.
    * 5 wrong passwords on the same account within 5 minutes → `429 too_many_attempts`; the account unlocks by
      itself after 60 real seconds. `details.retry_after_s` says how long is left.
    * Every sign-in, successful or not, is written to the access log (`login` / `login_failed`).

    Frontend: keep `access_token` in memory (not in `localStorage`) and send it in the
    `Authorization: Bearer <token>` header. `user.role` decides the screen: `astronaut` → the interactive body,
    `cmo` → the crew medical officer's queue, `earth` → Mission Control."""
    return await auth_service.login(session, body.username, body.password, secret=settings.jwt_secret)


@router.get("/me", response_model=User, summary="Who am I", responses={401: ERRORS[401]}, openapi_extra=roles(*ALL))
async def me(user: User = Depends(current_user)):
    """Returns the account from the token. Useful after a page reload and to always show, visibly, who is signed in."""
    return user


@router.post(
    "/logout",
    response_model=Ok,
    summary="Sign out (switching astronaut)",
    responses={401: ERRORS[401]},
    openapi_extra=roles(*ALL),
)
async def logout(
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
):
    """Invalidates the current token (the backend puts its `jti` on the revoked-token list). Written to the access
    log (`logout`).

    **Switching astronaut on the same workstation:** `logout` → delete the token and ALL loaded data from memory →
    close the `/events` connection → the "Who are you?" screen → `login` with another account → open `/events`
    again. The typing collector stops on sign-out, so keystrokes never reach another astronaut.

    Mock tokens (`mock-<username>`) stay valid after logout."""
    await auth_service.logout(
        session, request.state.token, secret=settings.jwt_secret, allow_mock=settings.allow_mock_tokens
    )
    return Ok()
