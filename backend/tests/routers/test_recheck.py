from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.clock import clock
from app.db import session as db
from app.db.models.alerts import Alert
from app.db.models.measurements import Measurement
from app.services import pipeline


async def load(alert_id: str) -> Alert:
    async with db.SessionLocal() as s:
        stmt = select(Alert).where(Alert.id == alert_id).options(selectinload(Alert.history))
        return await s.scalar(stmt)


async def due_now(alert_id: str) -> None:
    async with db.SessionLocal() as s:
        a = await s.get(Alert, alert_id)
        a.recheck_at = clock.now() - timedelta(minutes=1)
        await s.commit()


async def run(client) -> list:
    async with db.SessionLocal() as s:
        events = await pipeline.recheck_due(s, client._transport.app.state.data)
        await s.commit()
    return events


async def immune_alert_id() -> str:
    async with db.SessionLocal() as s:
        return await s.scalar(select(Alert.id).where(Alert.crew_id == "cm-2", Alert.topic == "immune"))


async def set_night_pulse(value: float) -> None:
    async with db.SessionLocal() as s:
        row = await s.scalar(
            select(Measurement).where(
                Measurement.crew_id == "cm-2",
                Measurement.metric_key == "night_pulse_bpm",
                Measurement.mission_day == 96,
            )
        )
        row.value = value
        await s.commit()


async def test_values_back_to_normal_resolve_the_alert(client):
    alert_id = await immune_alert_id()
    await set_night_pulse(54.0)
    await due_now(alert_id)
    events = await run(client)
    assert [(e.type, e.data["id"], e.data["state"]) for e in events] == [("alert.updated", alert_id, "resolved")]
    a = await load(alert_id)
    assert a.state == "resolved" and [h.action for h in a.history][-2:] == ["rechecked", "resolved"]
    assert a.history[-1].actor == "SHADOW" and a.history[-1].note == "Values back to normal."


async def test_values_still_high_move_the_alert_up_one_level(client):
    alert_id = await immune_alert_id()
    await due_now(alert_id)
    events = await run(client)
    assert [e.data["level"] for e in events] == [3]
    a = await load(alert_id)
    assert a.level == 3 and a.state == "escalated" and a.recheck_at > clock.now()
    assert a.history[-2].action == "rechecked" and "level 3" in a.history[-2].note
    assert a.packet_id  # level 3 → the alert goes to Earth
    assert await run(client) == []


async def test_no_new_data_waits(client):
    async with db.SessionLocal() as s:
        typing_id = await s.scalar(
            select(Alert.id).where(Alert.crew_id == "cm-2", Alert.topic == "behavioral", Alert.state != "resolved")
        )
    await due_now(typing_id)
    assert await run(client) == []
    assert (await load(typing_id)).state == "active"


async def test_not_due_is_left_alone(client):
    assert await run(client) == []
