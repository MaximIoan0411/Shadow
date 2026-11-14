"""Motorul asincron și sesiunea. Verificat (plan, secțiunea 5).

Motorul NU se creează la import, ci în init_engine(), apelată din lifespan. În restul codului se importă MODULUL:
    from app.db import session as db
    async with db.SessionLocal() as s: ...
(cu `from app.db.session import SessionLocal` ați primi None, valoarea de dinainte de pornire.)
"""
from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

engine: AsyncEngine | None = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None


def init_engine(url: str) -> AsyncEngine:
    """Apelată o singură dată, din lifespan. url = "sqlite+aiosqlite:///./shadow.sqlite"."""
    global engine, SessionLocal
    engine = create_async_engine(url)

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record) -> None:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")    # citiri în paralel cu o scriere
        cur.execute("PRAGMA foreign_keys=ON")     # SQLite le ignoră implicit
        cur.execute("PRAGMA busy_timeout=5000")   # așteaptă 5 s în loc de „database is locked”
        cur.close()

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    return engine


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependența FastAPI: o sesiune pe cerere. Serviciul face commit; publicarea evenimentelor vine după commit."""
    async with SessionLocal() as session:
        yield session
