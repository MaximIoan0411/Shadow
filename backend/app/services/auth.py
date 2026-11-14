import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clock import clock
from ..db.models.users import User as UserRow
from ..deps import ApiError
from ..schemas import LoginAccount, LoginResponse, Role, User
from ..security import access_log, lockout, passwords, tokens
from ..security.errors import AccountLocked, InvalidToken

MOCK_PREFIX = "mock-"
UNKNOWN_ACTOR = "unknown"
INVALID_CREDENTIALS = "Wrong username or password."
INVALID_TOKEN = "Invalid or expired token. Please sign in again."


def _to_user(row: UserRow, *, role: str | None = None, crew_id: str | None = None, from_token: bool = False) -> User:
    return User(
        id=row.id,
        username=row.username,
        display_name=row.display_name,
        initials=row.initials,
        role=Role(role if from_token else row.role),
        crew_id=crew_id if from_token else row.crew_id,
    )


async def _by_username(session: AsyncSession, username: str) -> UserRow | None:
    return await session.scalar(select(UserRow).where(UserRow.username == username))


async def _log(session: AsyncSession, action: str, row: UserRow | None, outcome: str) -> None:
    await access_log.write(
        session,
        at=clock.now(),
        actor=row.display_name if row else UNKNOWN_ACTOR,
        actor_role=row.role if row else UNKNOWN_ACTOR,
        action=action,
        resource=f"auth/{action.removesuffix('_failed')}",
        crew_id=row.crew_id if row else None,
        outcome=outcome,
    )


async def list_accounts(session: AsyncSession) -> list[LoginAccount]:
    rows = (await session.scalars(select(UserRow).order_by(UserRow.id))).all()
    return [
        LoginAccount(
            username=r.username,
            display_name=r.display_name,
            initials=r.initials,
            role=Role(r.role),
            crew_id=r.crew_id,
            location="earth" if r.role == Role.earth.value else "ship",
        )
        for r in rows
    ]


async def login(session: AsyncSession, username: str, password: str, *, secret: str) -> LoginResponse:
    row = await _by_username(session, username)
    try:
        lockout.check(username)
    except AccountLocked as e:
        await _log(session, "login_failed", row, "denied")
        await session.commit()
        raise ApiError(
            429,
            "too_many_attempts",
            "Too many failed attempts. This account is temporarily locked.",
            {"retry_after_s": e.retry_after_s},
        ) from None

    stored = row.password_hash if row else passwords.DUMMY_HASH
    ok = await asyncio.to_thread(passwords.verify, password, stored)
    if row is None or not ok:
        lockout.record_failure(username)
        await _log(session, "login_failed", row, "denied")
        await session.commit()
        raise ApiError(401, "invalid_credentials", INVALID_CREDENTIALS)

    lockout.clear(username)
    token, _claims = tokens.issue(user_id=row.id, role=row.role, crew_id=row.crew_id, secret=secret)
    await _log(session, "login", row, "allowed")
    await session.commit()
    return LoginResponse(access_token=token, expires_in=tokens.TTL_S, user=_to_user(row))


async def logout(session: AsyncSession, token: str, *, secret: str, allow_mock: bool) -> None:
    if allow_mock and token.startswith(MOCK_PREFIX):
        row = await _by_username(session, token.removeprefix(MOCK_PREFIX))
    else:
        claims = _decode(token, secret)
        await tokens.revoke(session, claims.jti, datetime.fromtimestamp(claims.exp, UTC))
        row = await session.get(UserRow, claims.sub)
    await _log(session, "logout", row, "allowed")
    await session.commit()


def _decode(token: str, secret: str) -> tokens.Claims:
    try:
        return tokens.decode(token, secret=secret)
    except InvalidToken:
        raise ApiError(401, "unauthorized", INVALID_TOKEN) from None


async def user_from_token(session: AsyncSession, token: str, *, secret: str, allow_mock: bool) -> User:
    if token.startswith(MOCK_PREFIX):
        row = await _by_username(session, token.removeprefix(MOCK_PREFIX)) if allow_mock else None
        if row is None:
            raise ApiError(401, "unauthorized", INVALID_TOKEN)
        return _to_user(row)

    claims = _decode(token, secret)
    if await tokens.is_revoked(session, claims.jti):
        raise ApiError(401, "unauthorized", INVALID_TOKEN)
    row = await session.get(UserRow, claims.sub)
    if row is None:
        raise ApiError(401, "unauthorized", INVALID_TOKEN)
    return _to_user(row, role=claims.role, crew_id=claims.crew_id, from_token=True)
