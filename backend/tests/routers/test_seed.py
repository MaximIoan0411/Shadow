import json

from asgi_lifespan import LifespanManager
from sqlalchemy import func, select

from app.db import session as db
from app.db.models.users import Crew, User
from app.main import USERS_SEED
from app.security import passwords

SEED = json.loads(USERS_SEED.read_text(encoding="utf-8"))["users"]


async def count(model) -> int:
    async with db.SessionLocal() as s:
        return await s.scalar(select(func.count()).select_from(model))


async def test_seed_creates_crew_and_accounts(client):
    assert await count(Crew) == 4
    assert await count(User) == 5
    async with db.SessionLocal() as s:
        crew = {c.id: c for c in (await s.scalars(select(Crew))).all()}
        earth = await s.get(User, "u-earth")
    assert set(crew) == {"cm-1", "cm-2", "cm-3", "cm-4"}
    assert [c.id for c in crew.values() if c.is_cmo] == ["cm-3"]
    assert crew["cm-2"].role_title == "Mission Specialist"
    assert earth.role == "earth" and earth.crew_id is None


async def test_passwords_are_stored_only_as_hashes(client):
    async with db.SessionLocal() as s:
        users = {u.username: u for u in (await s.scalars(select(User))).all()}
    for seed in SEED:
        stored = users[seed["username"]].password_hash
        assert seed["test_password"] not in stored
        assert passwords.verify(seed["test_password"], stored)
        assert not passwords.verify("wrong-password", stored)


async def test_each_account_has_its_own_password(client):
    async with db.SessionLocal() as s:
        cm2 = await s.get(User, "u-cm-2")
    assert passwords.verify("cm2-shadow", cm2.password_hash)
    assert not passwords.verify("cm1-shadow", cm2.password_hash)


async def test_seed_is_not_repeated_when_db_is_kept(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'keep.sqlite'}")
    from app.main import create_app

    async with LifespanManager(create_app()):
        pass
    monkeypatch.setenv("RESET_DB_ON_START", "false")
    async with LifespanManager(create_app()):
        assert await count(User) == 5
        assert await count(Crew) == 4
