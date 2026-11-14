from app.db import session as db
from app.db.models.sim import SimState
from app.ids import next_id, next_ids, next_seq


async def test_next_id_counts_up_with_padding(client):
    async with db.SessionLocal() as s:
        ids = [await next_id(s, "ta") for _ in range(3)]
        await s.commit()
    assert ids == ["ta-0001", "ta-0002", "ta-0003"]


async def test_prefixes_have_separate_counters(client):
    async with db.SessionLocal() as s:
        assert await next_id(s, "ta") == "ta-0001"
        assert await next_id(s, "tb") == "tb-0001"
        assert await next_id(s, "ta") == "ta-0002"
        await s.commit()


async def test_counter_persists_across_sessions(client):
    async with db.SessionLocal() as s:
        await next_id(s, "tst")
        await s.commit()
    async with db.SessionLocal() as s:
        assert await next_id(s, "tst") == "tst-0002"
        await s.commit()
    async with db.SessionLocal() as s:
        row = await s.get(SimState, "id:tst")
        assert row.value == {"n": 2}


async def test_rollback_does_not_advance_counter(client):
    async with db.SessionLocal() as s:
        await next_id(s, "ta")
        await s.commit()
    async with db.SessionLocal() as s:
        assert await next_id(s, "ta") == "ta-0002"
        await s.rollback()
    async with db.SessionLocal() as s:
        assert await next_id(s, "ta") == "ta-0002"
        await s.commit()


async def test_next_seq_per_direction(client):
    async with db.SessionLocal() as s:
        assert [await next_seq(s, "down") for _ in range(3)] == [1, 2, 3]
        assert await next_seq(s, "up") == 1
        await s.commit()
    async with db.SessionLocal() as s:
        assert await next_seq(s, "down") == 4
        await s.commit()


async def test_next_ids_reserves_a_block(client):
    async with db.SessionLocal() as s:
        assert await next_ids(s, "blk", 3) == ["blk-0001", "blk-0002", "blk-0003"]
        assert await next_id(s, "blk") == "blk-0004"
        assert await next_ids(s, "blk", 0) == []
        await s.commit()


async def test_width_grows_past_9999(client):
    async with db.SessionLocal() as s:
        s.add(SimState(key="id:rj", value={"n": 9999}))
        await s.flush()
        assert await next_id(s, "rj") == "rj-10000"
        await s.rollback()
