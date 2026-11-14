from sqlalchemy import select

from app.db import session as db
from app.db.models.alerts import Alert
from app.engine.cross_signals import detect, environmental_cause, weak_signals
from tests.conftest import auth


def signals(crew_id: str, day: int = 40, **observations) -> list:
    return weak_signals(crew_id, day, observations)


def test_weak_signal_thresholds():
    assert [f.title for f in signals("cm-1", sleep_hours=(5.0, 6.4))] == ["Sleep: -1.4 h"]
    assert signals("cm-1", sleep_hours=(5.6, 6.4)) == []
    assert [f.topic for f in signals("cm-1", keys_per_min=(190.0, 214.0))] == ["behavioral"]
    assert signals("cm-1", keys_per_min=(205.0, 214.0)) == []
    assert [f.title for f in signals("cm-1", night_pulse_bpm=(57.0, 54.0))] == ["Night pulse: +3.0 bpm"]


def test_environmental_cause_needs_three_members():
    two = signals("cm-1", sleep_hours=(5.0, 6.4)) + signals("cm-2", sleep_hours=(5.0, 6.6))
    assert environmental_cause(two, 4) == set()
    three = two + signals("cm-3", sleep_hours=(4.5, 6.1))
    assert environmental_cause(three, 4) == {"sleep_hours"}


def test_cross_signal_needs_two_pillars():
    one_pillar = signals("cm-2", 96, night_pulse_bpm=(61.0, 54.0), sleep_hours=(5.5, 6.6))
    assert detect(one_pillar) == []
    both = one_pillar + signals("cm-2", 95, keys_per_min=(173.0, 211.0))
    [x] = detect(both)
    assert x["pillars"] == ["behavioral", "immune"] and x["title"] == "Possible onset of an illness"
    assert len(x["signals"]) == 3 and 0 < x["confidence"] <= 0.9


async def alerts_by(**filters) -> list[Alert]:
    async with db.SessionLocal() as s:
        return list((await s.scalars(select(Alert).filter_by(**filters))).all())


async def test_day_40_crew_wide_sleep_alerts_are_environmental(client):
    day40 = await alerts_by(mission_day=40)
    assert {a.crew_id for a in day40} == {"cm-1", "cm-2", "cm-3", "cm-4"}
    assert {a.cause for a in day40} == {"environmental"} and {a.topic for a in day40} == {"behavioral"}
    assert "4 of 4 crew members" in day40[0].cause_explanation and "cabin" in day40[0].cause_explanation


async def test_cm2_immune_alert_is_individual(client):
    [immune] = await alerts_by(crew_id="cm-2", topic="immune")
    assert immune.cause == "individual" and immune.cause_explanation.startswith("Only you")


async def test_cm2_has_a_cross_signal_on_day_96(client):
    d = (await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("specialist2"))).json()
    [x] = d["cross_signals"]
    assert set(x["pillars"]) == {"immune", "behavioral"} and x["title"] == "Possible onset of an illness"
    assert any(s.startswith("Night pulse: +") for s in x["signals"]) and any(
        s.startswith("Typing:") for s in x["signals"]
    )
    cm1 = (await client.get("/api/v1/crew/cm-1/dashboard", headers=auth("comandant"))).json()
    assert cm1["cross_signals"] == []
    d40 = (await client.get("/api/v1/crew/cm-2/dashboard?as_of_day=40", headers=auth("specialist2"))).json()
    assert d40["cross_signals"] == []  # the crew-wide sleep change is environmental, not a personal signal
