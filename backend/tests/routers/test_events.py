import asyncio
import json

import pytest

from app import deps
from app.clock import clock
from app.routers.events import PING, stream
from app.services import mission as mission_service
from tests.conftest import auth

USERS = {
    "specialist2": deps.User(
        id="u-cm-2", username="specialist2", display_name="S2", initials="S2", role="astronaut", crew_id="cm-2"
    ),
    "medic": deps.User(id="u-cm-3", username="medic", display_name="CMO", initials="OM", role="cmo", crew_id="cm-3"),
    "earth": deps.User(id="u-earth", username="earth", display_name="FS", initials="MZ", role="earth", crew_id=None),
}


async def collect(user, events: list[tuple], *, ping_after_s=0.05, max_items=10) -> list[str]:
    """Runs the SSE generator for one user while `events` are published, then disconnects."""
    q = deps.subscribe()
    for type_, data, crew_id in events:
        deps.publish(type_, data, crew_id)
    done = {"n": 0}

    async def disconnected():
        done["n"] += 1
        return done["n"] > max_items

    out = []
    gen = stream(user, q, disconnected, ping_after_s=ping_after_s)
    async for chunk in gen:
        out.append(chunk)
        if chunk == PING:
            break
    await gen.aclose()
    assert q not in deps._subscribers
    return out


def types(chunks: list[str]) -> list[str]:
    return [json.loads(c.split("data: ", 1)[1])["type"] if c != PING else "ping" for c in chunks]


@pytest.fixture
def events():
    return [
        ("alert.created", {"id": "al-x", "level": 2}, "cm-1"),
        ("dashboard.changed", {"reason": "checkin"}, "cm-2"),
        ("mission.tick", mission_service.tick_data(), None),
        ("packet.sent", {"id": "pk-x"}, "cm-1"),
    ]


async def test_astronaut_does_not_get_other_members_events(client, events):
    assert types(await collect(USERS["specialist2"], events)) == ["dashboard.changed", "mission.tick", "ping"]


async def test_cmo_gets_everything(client, events):
    assert types(await collect(USERS["medic"], events)) == [
        "alert.created",
        "dashboard.changed",
        "mission.tick",
        "packet.sent",
        "ping",
    ]


async def test_earth_gets_only_mission_and_packets(client, events):
    assert types(await collect(USERS["earth"], events)) == ["mission.tick", "packet.sent", "ping"]


async def test_event_time_is_mission_time(client):
    chunks = await collect(USERS["medic"], [("mission.tick", mission_service.tick_data(), None)])
    event = json.loads(chunks[0].split("data: ", 1)[1])
    assert event["at"].startswith("2027-04-15T07:0")
    assert event["data"]["mission_day"] == 96 and event["data"]["sim_now"].startswith("2027-04-15")
    assert chunks[0].startswith(f"id: {event['id']}\nevent: mission.tick\ndata: ")


async def test_ping_when_nothing_happens(client):
    assert await collect(USERS["medic"], [], ping_after_s=0.01) == [PING]


async def test_ticker_publishes_every_second(client, monkeypatch):
    monkeypatch.setattr(mission_service, "TICK_S", 0.01)
    q = deps.subscribe()
    task = asyncio.create_task(mission_service.mission_ticker())
    try:
        await asyncio.sleep(0.05)
    finally:
        task.cancel()
        deps.unsubscribe(q)
    ticks = [q.get_nowait() for _ in range(q.qsize())]
    assert len(ticks) >= 2 and {t["type"] for t in ticks} == {"mission.tick"}
    assert ticks[0]["data"]["mission_day"] == clock.mission_day()


async def test_clock_change_sends_a_tick(client):
    q = deps.subscribe()
    try:
        await client.put("/api/v1/sim/clock", headers=auth("medic"), json={"time_scale": 120})
        got = [q.get_nowait()["type"] for _ in range(q.qsize())]
    finally:
        deps.unsubscribe(q)
    assert got == ["mission.tick"]


async def test_events_endpoint_requires_auth(client):
    assert (await client.get("/api/v1/events")).status_code == 401


def test_cmo_gets_a_colleagues_alert_live_only_from_level_2():
    from app.deps import visible_to
    from app.schemas import Role, User

    cmo = User(id="u-cm-3", username="medic", display_name="CMO", initials="OM", role=Role.cmo, crew_id="cm-3")

    def alert(level: int, crew_id: str) -> dict:
        return {"type": "alert.created", "crew_id": crew_id, "data": {"level": level, "title": "Typing slower"}}

    assert not visible_to(cmo, alert(1, "cm-2"))
    assert visible_to(cmo, alert(2, "cm-2")) and visible_to(cmo, alert(3, "cm-2"))
    assert visible_to(cmo, alert(1, "cm-3"))  # their own
    assert visible_to(cmo, {"type": "dashboard.changed", "crew_id": "cm-2", "data": {"reason": "checkin"}})


def test_a_client_that_stops_reading_does_not_grow_without_limit():
    from app import deps

    q = deps.subscribe()
    try:
        for i in range(deps.SUBSCRIBER_QUEUE_MAX + 50):
            deps.publish("mission.tick", {"n": i})
        assert q.qsize() == deps.SUBSCRIBER_QUEUE_MAX
        assert q.get_nowait()["data"] == {"n": 50}  # the oldest ones were dropped
    finally:
        deps.unsubscribe(q)
