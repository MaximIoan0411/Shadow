import pytest
from sqlalchemy import func, select

from app import deps
from app.db import session as db
from app.db.models.measurements import Checkin as CheckinRow
from tests.conftest import auth

A = auth("specialist2")
URL = "/api/v1/crew/cm-2/checkins"
BODY = {
    "mood": 4,
    "systolic_mmhg": 112,
    "diastolic_mmhg": 72,
    "pulse_bpm": 58,
    "glucose_mg_dl": 92,
    "temperature_c": 37.3,
    "sleep_hours": 5.5,
    "meals_eaten": "some",
}


async def test_schema_comes_from_data(client):
    data = client._transport.app.state.data
    r = (await client.get("/api/v1/checkin/schema", headers=A)).json()
    assert [i["key"] for i in r["indicators"]] == [i.key for i in data.checkin.indicators]


async def test_impossible_value_is_rejected_rest_saved(client):
    r = await client.post(URL, headers=A, json={**BODY, "temperature_c": 41.9})
    assert r.status_code == 201
    body = r.json()
    assert [(x["field"], x["value"], x["reason"]) for x in body["rejected"]] == [("temperature_c", 41.9, "implausible")]
    assert body["checkin"]["values"]["temperature_c"] is None
    assert body["checkin"]["values"]["systolic_mmhg"] == 112 and body["checkin"]["mission_day"] == 96


async def test_second_checkin_replaces_the_first(client):
    first = (await client.post(URL, headers=A, json=BODY)).json()
    second = (await client.post(URL, headers=A, json={**BODY, "mood": 2})).json()
    assert second["checkin"]["id"] == first["checkin"]["id"]
    today = (await client.get(f"{URL}/today", headers=A)).json()
    assert today["values"]["mood"] == 2
    async with db.SessionLocal() as s:
        n = await s.scalar(
            select(func.count())
            .select_from(CheckinRow)
            .where(CheckinRow.crew_id == "cm-2", CheckinRow.mission_day == 96)
        )
        row = await s.scalar(select(CheckinRow).where(CheckinRow.crew_id == "cm-2", CheckinRow.mission_day == 96))
    assert n == 1 and row.source == "manual"


async def test_perception_gap_for_cm2_on_day_96(client):
    body = (await client.post(URL, headers=A, json=BODY)).json()
    gap = body["perception_gap"]
    assert gap["self_reported_mood"] == 4 and gap["self_score"] == 80
    # until T19/T20 only the night pulse and sleep scores exist: night +7 bpm → 58, sleep −1.1 h → ~72
    assert 60 <= gap["objective_score"] <= 70 and gap["gap"] == pytest.approx(80 - gap["objective_score"])
    assert gap["contributing_signals"][0].startswith("Night pulse: +")
    assert any(s.startswith("Sleep: -") for s in gap["contributing_signals"])
    expected = "alert" if gap["gap"] >= 25 else "watch" if gap["gap"] >= 15 else "ok"
    assert gap["status"] == expected
    # with the typing score (T19) the gap passes 25 and becomes "alert"


async def test_streak_and_message(client):
    body = (await client.post(URL, headers=A, json=BODY)).json()
    assert body["streak"]["key"] == "checkin" and body["streak"]["days"] == 96 and body["streak"]["best"] == 96
    assert body["message"] == "Check-in saved. 96 days in a row."


async def test_events_after_commit(client):
    q = deps.subscribe()
    try:
        await client.post(URL, headers=A, json=BODY)
        events = [q.get_nowait() for _ in range(q.qsize())]
    finally:
        deps.unsubscribe(q)
    types = [e["type"] for e in events]
    assert "dashboard.changed" in types
    assert next(e for e in events if e["type"] == "dashboard.changed")["data"] == {"reason": "checkin"}


async def test_frozen_value_three_days_in_a_row(client):
    async with db.SessionLocal() as s:
        rows = (
            await s.scalars(
                select(CheckinRow).where(CheckinRow.crew_id == "cm-2", CheckinRow.mission_day.in_([94, 95]))
            )
        ).all()
        for row in rows:
            row.glucose_mg_dl = 92.0
            row.temperature_c = 36.5
            row.source = "manual"
        await s.commit()
    body = (await client.post(URL, headers=A, json=BODY)).json()
    assert [(x["field"], x["reason"]) for x in body["rejected"]] == [("glucose_mg_dl", "frozen_sensor")]
    assert body["checkin"]["values"]["glucose_mg_dl"] is None


async def test_simulated_history_does_not_count_as_frozen(client):
    async with db.SessionLocal() as s:
        rows = (
            await s.scalars(
                select(CheckinRow).where(CheckinRow.crew_id == "cm-2", CheckinRow.mission_day.in_([94, 95]))
            )
        ).all()
        for row in rows:
            row.temperature_c = 37.3
        await s.commit()
    body = (await client.post(URL, headers=A, json=BODY)).json()
    assert body["rejected"] == [] and body["checkin"]["values"]["temperature_c"] == 37.3


async def test_history_newest_first(client):
    rows = (await client.get(f"{URL}?from_day=90&to_day=96", headers=A)).json()
    assert [r["mission_day"] for r in rows] == [96, 95, 94, 93, 92, 91, 90]


async def test_other_crew_forbidden(client):
    assert (await client.post(URL, headers=auth("comandant"), json=BODY)).status_code == 403
