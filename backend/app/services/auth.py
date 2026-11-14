"""Conturi, login, logout, tokenuri. TASK T07.

Vezi backend/handoff/tasks/T07-*.md pentru pași, fișiere și criteriile de acceptare.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import LoginAccount, LoginResponse, User


async def list_accounts(session: AsyncSession) -> list[LoginAccount]:
    raise NotImplementedError("T07")


async def login(session: AsyncSession, username: str, password: str, *, secret: str) -> LoginResponse:
    """lockout.check → passwords.verify (asyncio.to_thread; DUMMY_HASH dacă nu există contul) → record_failure / clear
    → tokens.issue → access_log.write(login | login_failed). Aruncă ApiError(401 | 429)."""
    raise NotImplementedError("T07")


async def logout(session: AsyncSession, claims) -> None:
    raise NotImplementedError("T07")


async def user_from_token(session: AsyncSession, token: str, *, secret: str, allow_mock: bool) -> User:
    """Folosită de deps.current_user. tokens.decode → tokens.is_revoked → încărcarea contului. Cu allow_mock,
    acceptă și „mock-<utilizator>”. Aruncă ApiError(401)."""
    raise NotImplementedError("T07")
