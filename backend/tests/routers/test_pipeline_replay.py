from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import repos
from app.db import session as db
from app.db.models.alerts import Alert
from app.db.models.measurements import Measurement
from app.services import pipeline


async def alerts(**filters) -> list[Alert]:
    stmt = select(Alert).options(selectinload(Alert.steps), selectinload(Alert.history)).filter_by(**filters)
    async with db.SessionLocal() as s:
        return list((await s.scalars(stmt)).all())


async def test_cm2_immune_alert_created_day_94_escalated_day_95(client):
    [alert] = await alerts(crew_id="cm-2", topic="immune")
    assert alert.mission_day == 94
    assert alert.level == 2 and alert.status == "alert" and alert.state == "escalated"
    assert alert.recommendation_id == "immune-2-1"
    assert alert.title == "Night pulse +7 bpm, 3 nights in a row"
    data = client._transport.app.state.data
    actions = [(h.action, h.actor, h.at) for h in alert.history]
    assert actions == [
        ("created", "SHADOW", pipeline.review_time(data, 94)),
        ("escalated", "SHADOW", pipeline.review_time(data, 95)),
    ]
    assert [e["metric_key"] for e in alert.evidence] == ["night_pulse_bpm", "temperature_c", "sleep_hours"]
    red_steps = client._transport.app.state.data.catalog.by_id()["immune-2-1"].steps
    assert [s.step_id for s in alert.steps][0] == "st-1"
    assert [s.text for s in alert.steps] == red_steps
    assert alert.recheck_at > alert.created_at


async def test_no_other_crew_has_an_immune_alert(client):
    assert [a.crew_id for a in await alerts(topic="immune")] == ["cm-2"]


async def test_process_creates_alert_and_returns_events(client):
    app_data = client._transport.app.state.data
    async with db.SessionLocal() as s:
        last = await repos.latest(s, "cm-1", "night_pulse_bpm", 96)
        s.add(
            Measurement(
                crew_id="cm-1",
                metric_key="night_pulse_bpm",
                value=last.value + 5,
                unit="bpm",
                measured_at=last.t + timedelta(minutes=30),
                mission_day=96,
                source="device",
                device_id="wearable-cm-1",
            )
        )
        await s.flush()
        result = await pipeline.process(s, "cm-1", {"night_pulse_bpm"}, day=96, data=app_data, reason="recheck")
        await s.commit()
    assert len(result.alerts_created) == 1 and result.alerts_updated == []
    types = [e.type for e in result.events]
    assert types == ["alert.created", "dashboard.changed"]
    assert result.events[0].data["level"] == 1 and result.events[0].crew_id == "cm-1"
    assert result.events[1].data == {"reason": "recheck"}
    [alert] = await alerts(crew_id="cm-1", topic="immune")
    assert alert.level == 1 and alert.state == "active" and alert.history[0].action == "created"


async def test_process_updates_existing_alert(client):
    app_data = client._transport.app.state.data
    async with db.SessionLocal() as s:
        result = await pipeline.process(s, "cm-2", {"night_pulse_bpm"}, day=96, data=app_data)
        await s.commit()
    assert result.alerts_created == [] and len(result.alerts_updated) == 1
    assert [e.type for e in result.events] == ["alert.updated"]
    assert len(await alerts(crew_id="cm-2", topic="immune")) == 1


async def test_unrelated_metric_runs_no_rules(client):
    app_data = client._transport.app.state.data
    async with db.SessionLocal() as s:
        result = await pipeline.process(s, "cm-2", {"glucose_mg_dl"}, day=96, data=app_data)
    assert result.alerts_created == [] and result.alerts_updated == [] and result.events == []
