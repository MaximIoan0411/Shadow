import logging

import pytest
from sqlalchemy import delete, select, update

from app.db import session as db
from app.db.models.security import AccessLog
from app.main import check_access_log
from app.security import access_log
from tests.conftest import auth


async def all_entries() -> list[AccessLog]:
    async with db.SessionLocal() as s:
        return list((await s.scalars(select(AccessLog).order_by(AccessLog.id))).all())


@pytest.fixture
def new_entries():
    # every test starts with an empty database, so everything in the table was written by the test
    return all_entries


async def test_denied_read_is_logged(client, new_entries):
    r = await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("comandant"))
    assert r.status_code == 403
    [e] = await new_entries()
    assert (e.action, e.outcome, e.crew_id) == ("access_denied", "denied", "cm-2")
    assert e.actor == "Commander" and e.actor_role == "astronaut"
    assert e.resource == "crew/cm-2/dashboard"


async def test_cmo_reading_another_member_is_logged(client, new_entries):
    r = await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("medic"))
    assert r.status_code == 200
    [e] = await new_entries()
    assert (e.action, e.outcome, e.crew_id, e.actor_role) == ("read_dashboard", "allowed", "cm-2", "cmo")


async def test_astronaut_reading_own_data_is_not_logged(client, new_entries):
    assert (await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("specialist2"))).status_code == 200
    assert await new_entries() == []


async def test_earth_role_denied_is_logged(client, new_entries):
    assert (await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("earth"))).status_code == 403
    [e] = await new_entries()
    assert (e.action, e.actor_role, e.crew_id) == ("access_denied", "earth", "cm-2")


async def test_cmo_reading_alert_is_logged(client, new_entries):
    own = (await client.get("/api/v1/crew/cm-2/alerts", headers=auth("specialist2"))).json()
    alert_id = next(a["id"] for a in own if a["topic"] == "immune")
    assert (await client.get(f"/api/v1/alerts/{alert_id}", headers=auth("medic"))).status_code == 200
    [e] = await new_entries()
    assert (e.action, e.resource, e.crew_id) == ("read_alert", f"alerts/{alert_id}", "cm-2")


async def test_no_secrets_in_log(client, new_entries):
    await client.post("/api/v1/auth/login", json={"username": "specialist2", "password": "cm2-shadow"})
    await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("medic"))
    text = repr([(e.actor, e.action, e.resource, e.crew_id, e.outcome) for e in await new_entries()])
    assert "cm2-shadow" not in text and "mock-" not in text and "Bearer" not in text


async def test_access_log_endpoint_newest_first_and_filtered(client):
    await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("medic"))
    await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("comandant"))

    mine = (await client.get("/api/v1/access-log", headers=auth("specialist2"))).json()
    assert mine and all(e["crew_id"] == "cm-2" for e in mine)
    assert [e["id"] for e in mine] == sorted((e["id"] for e in mine), reverse=True)
    assert mine[0]["action"] == "access_denied"

    ignored = (await client.get("/api/v1/access-log?crew_id=cm-1", headers=auth("specialist2"))).json()
    assert all(e["crew_id"] == "cm-2" for e in ignored)

    everything = (await client.get("/api/v1/access-log?limit=500", headers=auth("medic"))).json()
    assert {e["crew_id"] for e in everything} >= {"cm-2"}
    assert len((await client.get("/api/v1/access-log?limit=1", headers=auth("medic"))).json()) == 1


async def test_access_log_endpoint_forbidden_for_earth(client):
    assert (await client.get("/api/v1/access-log", headers=auth("earth"))).status_code == 403


async def chain_ok() -> bool:
    async with db.SessionLocal() as s:
        return await access_log.verify_chain(s)


async def test_chain_links_every_entry_and_detects_changes(client):
    for user in ("medic", "comandant", "medic"):
        await client.get("/api/v1/crew/cm-2/dashboard", headers=auth(user))
    rows = await all_entries()
    assert [r.id for r in rows] == [1, 2, 3] and rows[0].prev_hash == access_log.GENESIS
    assert rows[1].prev_hash == rows[0].hash and rows[2].prev_hash == rows[1].hash
    assert await chain_ok()

    async with db.SessionLocal() as s:  # someone edits a row directly in the database
        await s.execute(update(AccessLog).where(AccessLog.id == 2).values(actor="Nobody"))
        await s.commit()
    assert not await chain_ok()


async def test_chain_detects_a_deleted_entry(client):
    for user in ("medic", "comandant", "medic"):
        await client.get("/api/v1/crew/cm-2/dashboard", headers=auth(user))
    async with db.SessionLocal() as s:
        await s.execute(delete(AccessLog).where(AccessLog.id == 2))
        await s.commit()
    assert not await chain_ok()


async def hide_the_refused_read() -> None:
    """Someone edits the database directly: the commander's refused attempt (entry 2) now says `allowed`."""
    async with db.SessionLocal() as s:
        await s.execute(update(AccessLog).where(AccessLog.id == 2).values(outcome="allowed"))
        await s.commit()


async def test_the_running_app_reports_a_changed_log(client):
    for user in ("medic", "comandant", "medic"):
        await client.get("/api/v1/crew/cm-2/dashboard", headers=auth(user))
    before = (await client.get("/api/v1/access-log/integrity", headers=auth("specialist2"))).json()
    assert before["intact"] is True and before["entries"] == 3

    await hide_the_refused_read()
    after = (await client.get("/api/v1/access-log/integrity", headers=auth("medic"))).json()
    assert after["intact"] is False and after["entries"] == 3


async def test_a_log_changed_while_the_app_was_stopped_is_reported_at_startup(client, caplog):
    for user in ("medic", "comandant", "medic"):
        await client.get("/api/v1/crew/cm-2/dashboard", headers=auth(user))
    with caplog.at_level(logging.ERROR):
        await check_access_log()
    assert "BROKEN" not in caplog.text

    await hide_the_refused_read()
    with caplog.at_level(logging.ERROR):
        await check_access_log()
    assert "access log: the hash chain is BROKEN" in caplog.text


async def test_integrity_check_is_for_the_crew_only(client):
    assert (await client.get("/api/v1/access-log/integrity", headers=auth("earth"))).status_code == 403
    assert (await client.get("/api/v1/access-log/integrity")).status_code == 401


async def test_parallel_requests_keep_one_chain(client):
    import asyncio

    await asyncio.gather(*(client.get("/api/v1/crew/cm-2/dashboard", headers=auth("medic")) for _ in range(12)))
    rows = await all_entries()
    assert [r.id for r in rows] == list(range(1, 13)) and await chain_ok()


async def test_reset_keeps_the_access_log_and_is_written_to_it(client):
    await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("medic"))
    assert (await client.post("/api/v1/sim/reset", headers=auth("specialist2"))).status_code == 200
    rows = await all_entries()
    assert [(r.action, r.actor) for r in rows] == [
        ("read_dashboard", "Crew Medical Officer"),
        ("reset", "Mission Specialist 2"),
    ]
    assert await chain_ok()


async def test_escalating_and_opening_a_packet_are_logged(client):
    from datetime import timedelta

    from app.clock import clock
    from app.link import scheduler

    t0 = clock.now()
    clock.freeze(t0)
    own = (await client.get("/api/v1/crew/cm-2/alerts", headers=auth("specialist2"))).json()
    alert_id = next(a["id"] for a in own if a["topic"] == "immune")
    r = await client.post(f"/api/v1/alerts/{alert_id}/escalate", headers=auth("medic"), json={"to_level": 3})
    packet_id = r.json()["packet_id"]
    assert [(e.action, e.actor_role, e.crew_id) for e in await all_entries()] == [("escalate", "cmo", "cm-2")]

    # before it arrives there is no content to read, so nothing to log
    await client.get(f"/api/v1/link/packets/{packet_id}", headers=auth("earth"))
    assert len(await all_entries()) == 1
    data = client._transport.app.state.data
    for moment in (t0, t0 + timedelta(seconds=700)):
        clock.freeze(moment)
        async with db.SessionLocal() as s:
            await scheduler.step(s, data)
            await s.commit()
    detail = (await client.get(f"/api/v1/link/packets/{packet_id}", headers=auth("earth"))).json()
    assert detail["payload"] is not None
    last = (await all_entries())[-1]
    assert (last.action, last.actor_role, last.crew_id, last.resource) == (
        "read_packet",
        "earth",
        "cm-2",
        f"link/packets/{packet_id}",
    )
    # the astronaut sees both in their own access log
    mine = (await client.get("/api/v1/access-log", headers=auth("specialist2"))).json()
    assert [e["action"] for e in mine] == ["read_packet", "escalate"]
