import time
from datetime import timedelta

from sqlalchemy import func, select

from app.clock import clock
from app.db import session as db
from app.db.models.alerts import Alert
from app.db.models.measurements import Checkin, Measurement
from app.link import scheduler
from tests.conftest import auth

A, C, E = auth("specialist2"), auth("medic"), auth("earth")


async def alerts_now() -> list[tuple]:
    async with db.SessionLocal() as s:
        rows = (await s.scalars(select(Alert).order_by(Alert.id))).all()
        return [(a.crew_id, a.topic, a.level, a.state, a.mission_day) for a in rows]


async def test_reset_brings_back_day_96_and_the_replay_alerts(client):
    before = await alerts_now()
    await client.put("/api/v1/sim/clock", headers=C, json={"mission_day": 98})
    await client.post("/api/v1/crew/cm-2/checkins", headers=A, json={"mood": 3})
    await client.post("/api/v1/sim/sep/start", headers=C, json={})
    started = time.perf_counter()
    r = await client.post("/api/v1/sim/reset", headers=C)
    took = time.perf_counter() - started
    assert r.status_code == 200 and took < 5
    assert (await client.get("/api/v1/mission", headers=A)).json()["mission_day"] == 96
    assert await alerts_now() == before
    assert (await client.get("/api/v1/radiation/status", headers=A)).json()["event"] is None
    assert (await client.get("/api/v1/crew/cm-2/checkins/today", headers=A)).json() is None


async def test_jump_to_day_98_creates_days_97_and_98(client):
    r = await client.put("/api/v1/sim/clock", headers=C, json={"mission_day": 98})
    assert r.status_code == 200 and r.json()["mission_day"] == 98
    assert r.json()["sim_now"].startswith("2027-04-17T07:0")
    async with db.SessionLocal() as s:
        nights = (
            await s.scalars(
                select(Measurement.mission_day).where(
                    Measurement.crew_id == "cm-2", Measurement.metric_key == "night_pulse_bpm"
                )
            )
        ).all()
        checkins = await s.scalar(
            select(func.count()).select_from(Checkin).where(Checkin.crew_id == "cm-2", Checkin.mission_day == 97)
        )
    assert sorted(set(nights))[-3:] == [96, 97, 98] and len(nights) == 98 and checkins == 1
    timeline = (await client.get("/api/v1/crew/cm-2/timeline", headers=A)).json()
    assert len(timeline["days"]) == 98 and timeline["days"][-1]["pillars"]["immune"] == "alert"
    immune = next(a for a in (await client.get("/api/v1/crew/cm-2/alerts", headers=A)).json() if a["topic"] == "immune")
    assert immune["level"] >= 2


async def test_forged_packet_is_rejected_by_the_queue(client):
    t0 = clock.now()
    clock.freeze(t0)
    r = await client.post("/api/v1/demo/inject-spoof", headers=E)
    assert r.status_code == 200 and r.json()["status"] == "queued"
    packet_id = r.json()["id"]
    data = client._transport.app.state.data
    for moment in (t0, t0 + timedelta(seconds=700)):
        clock.freeze(moment)
        async with db.SessionLocal() as s:
            await scheduler.step(s, data)
            await s.commit()
    detail = (await client.get(f"/api/v1/link/packets/{packet_id}", headers=E)).json()
    assert (
        detail["status"] == "rejected"
        and detail["signature_valid"] is False
        and detail["reject_reason"] == "bad_signature"
    )
    rejections = (await client.get("/api/v1/security/rejections", headers=C)).json()
    assert rejections[0]["source"] == packet_id and rejections[0]["kind"] == "bad_signature"


async def test_frozen_sensor_demo(client):
    r = await client.post("/api/v1/demo/frozen-sensor", headers=C)
    assert r.status_code == 200 and r.json()["kind"] == "frozen_sensor" and r.json()["crew_id"] == "cm-4"
    rows = (await client.get("/api/v1/security/rejections", headers=C)).json()
    assert [x["kind"] for x in rows] == ["frozen_sensor"]
