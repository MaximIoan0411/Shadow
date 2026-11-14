from sqlalchemy.ext.asyncio import AsyncSession

from .db.models.sim import SimState

WIDTH = 4


async def _bump(session: AsyncSession, key: str, count: int = 1) -> int:
    row = await session.get(SimState, key)
    if row is None:
        n = count
        session.add(SimState(key=key, value={"n": n}))
    else:
        n = int(row.value.get("n", 0)) + count
        row.value = {**row.value, "n": n}
    await session.flush()
    return n


def _format(prefix: str, n: int) -> str:
    return f"{prefix}-{n:0{WIDTH}d}"


async def next_id(session: AsyncSession, prefix: str) -> str:
    return _format(prefix, await _bump(session, f"id:{prefix}"))


async def next_ids(session: AsyncSession, prefix: str, count: int) -> list[str]:
    if count <= 0:
        return []
    last = await _bump(session, f"id:{prefix}", count)
    return [_format(prefix, n) for n in range(last - count + 1, last + 1)]


async def next_seq(session: AsyncSession, direction: str) -> int:
    return await _bump(session, f"seq:{direction}")
