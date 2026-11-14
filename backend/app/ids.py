from sqlalchemy.ext.asyncio import AsyncSession

from .db.models.sim import SimState

WIDTH = 4


async def _bump(session: AsyncSession, key: str) -> int:
    row = await session.get(SimState, key)
    if row is None:
        n = 1
        session.add(SimState(key=key, value={"n": n}))
    else:
        n = int(row.value.get("n", 0)) + 1
        row.value = {**row.value, "n": n}
    await session.flush()
    return n


async def next_id(session: AsyncSession, prefix: str) -> str:
    n = await _bump(session, f"id:{prefix}")
    return f"{prefix}-{n:0{WIDTH}d}"


async def next_seq(session: AsyncSession, direction: str) -> int:
    return await _bump(session, f"seq:{direction}")
