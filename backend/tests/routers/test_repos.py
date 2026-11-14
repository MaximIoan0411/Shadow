from datetime import timedelta

from sqlalchemy import delete

from app.db import repos
from app.db import session as db
from app.db.models.measurements import Measurement


async def test_night_pulse_of_cm2_days_90_to_96(client):
    async with db.SessionLocal() as s:
        points = await repos.series(s, "cm-2", "night_pulse_bpm", 90, 96)
    assert [p.day for p in points] == list(range(90, 97))
    assert points[-1].value > points[0].value + 5
    assert all(points[i].day < points[i + 1].day for i in range(len(points) - 1))
    assert all(p.t.hour == 3 for p in points)


async def test_checkin_only_metric(client):
    async with db.SessionLocal() as s:
        mood = await repos.series(s, "cm-2", "mood", 1, 96)
    assert len(mood) == 95 and {p.value for p in mood} <= {1, 2, 3, 4, 5}
    assert mood[94].value == 4


async def test_checkin_fills_days_without_measurement(client):
    async with db.SessionLocal() as s:
        await s.execute(
            delete(Measurement).where(
                Measurement.crew_id == "cm-2", Measurement.metric_key == "temperature_c", Measurement.mission_day == 50
            )
        )
        await s.commit()
        points = await repos.series(s, "cm-2", "temperature_c", 49, 51)
    assert [p.day for p in points] == [49, 50, 51]
    assert points[1].t.hour == 7


async def test_one_value_per_day_keeps_the_last(client):
    async with db.SessionLocal() as s:
        first = await repos.latest(s, "cm-1", "night_pulse_bpm", 10)
        s.add(
            Measurement(
                crew_id="cm-1",
                metric_key="night_pulse_bpm",
                value=99.0,
                unit="bpm",
                measured_at=first.t + timedelta(hours=1),
                mission_day=10,
                source="device",
                device_id="wearable-cm-1",
            )
        )
        await s.commit()
        points = await repos.series(s, "cm-1", "night_pulse_bpm", 10, 10)
    assert len(points) == 1 and points[0].value == 99.0


async def test_series_all_crew(client):
    async with db.SessionLocal() as s:
        all_crew = await repos.series_all_crew(s, "sleep_hours", 40, 41)
    assert list(all_crew) == ["cm-1", "cm-2", "cm-3", "cm-4"]
    assert all(len(p) == 2 for p in all_crew.values())


async def test_latest(client):
    async with db.SessionLocal() as s:
        p = await repos.latest(s, "cm-2", "night_pulse_bpm", 94)
        none = await repos.latest(s, "cm-2", "unknown_metric", 96)
    assert p.day == 94 and none is None


async def test_recent_device_values(client):
    async with db.SessionLocal() as s:
        base = await repos.latest(s, "cm-3", "night_pulse_bpm", 96)
        for i, v in enumerate([60.0, 61.0, 62.0, 63.0]):
            s.add(
                Measurement(
                    crew_id="cm-3",
                    metric_key="night_pulse_bpm",
                    value=v,
                    unit="bpm",
                    measured_at=base.t + timedelta(minutes=i + 1),
                    mission_day=96,
                    source="device",
                    device_id="wearable-cm-3",
                )
            )
        await s.commit()
        values = await repos.recent_device_values(s, "wearable-cm-3", "night_pulse_bpm", 3)
        nothing = await repos.recent_device_values(s, "wearable-cm-9", "night_pulse_bpm", 3)
    assert values == [61.0, 62.0, 63.0] and nothing == []
