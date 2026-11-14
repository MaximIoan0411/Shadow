"""Id-urile cu prefix din contract (al-0001, pk-0007, ck-0096 …). TASK T04.

Contorul fiecărui prefix stă în sim_state (cheia "id:<prefix>"), incrementat în ACEEAȘI tranzacție cu scrierea.
"""
from sqlalchemy.ext.asyncio import AsyncSession

WIDTH = 4  # al-0001


async def next_id(session: AsyncSession, prefix: str) -> str:
    """Întoarce "<prefix>-NNNN" și crește contorul. Nu face commit."""
    raise NotImplementedError("T04")


async def next_seq(session: AsyncSession, direction: str) -> int:
    """Următorul seq pentru coada navă ↔ Pământ, pe direcție ("down" / "up"). Cheia sim_state: "seq:<direction>"."""
    raise NotImplementedError("T04")
