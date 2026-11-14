import asyncio
import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..datafiles import DataBundle
from ..security import passwords
from .models.users import Crew, User

ROLE_TITLES = {
    "cm-1": "Commander",
    "cm-2": "Mission Specialist",
    "cm-3": "Crew Medical Officer",
    "cm-4": "Flight Engineer",
}


def _read_users(path: str) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["users"]


async def seed_crew_and_users(session: AsyncSession, users_json_path: str) -> None:
    if await session.scalar(select(func.count()).select_from(User)):
        return
    accounts = await asyncio.to_thread(_read_users, users_json_path)

    for u in accounts:
        if u["crew_id"] is None:
            continue
        session.add(
            Crew(
                id=u["crew_id"],
                display_name=u["display_name"],
                initials=u["initials"],
                role_title=ROLE_TITLES.get(u["crew_id"], u["display_name"]),
                is_cmo=u["role"] == "cmo",
            )
        )
    await session.flush()

    hashes = await asyncio.gather(*(asyncio.to_thread(passwords.hash, u["test_password"]) for u in accounts))
    for u, password_hash in zip(accounts, hashes, strict=True):
        session.add(
            User(
                id=u["id"],
                username=u["username"],
                password_hash=password_hash,
                display_name=u["display_name"],
                initials=u["initials"],
                role=u["role"],
                crew_id=u["crew_id"],
            )
        )
    await session.flush()


async def seed_history(session: AsyncSession, data: DataBundle, until_day: int) -> None:
    raise NotImplementedError("T11")
