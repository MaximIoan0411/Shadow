"""T02: SimClock — timpul misiunii (ziua 96, 07:00, ×scale), cu time.monotonic() controlat din test."""

from datetime import UTC, datetime, timedelta

import pytest

from app import clock as clock_module
from app.clock import SimClock

MISSION_START = datetime(2027, 1, 10, tzinfo=UTC)  # data/scenario/scenario.json → start


class FakeMonotonic:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def mono(monkeypatch):
    fake = FakeMonotonic()
    monkeypatch.setattr(clock_module._time, "monotonic", fake)
    return fake


@pytest.fixture
def clk(mono):
    c = SimClock()
    c.start(mission_start=MISSION_START, day=96, time_hhmm="07:00", scale=60)
    return c


def test_starts_on_day_96_at_0700_utc(clk):
    now = clk.now()
    assert now == MISSION_START + timedelta(days=95, hours=7)
    assert now.tzinfo is not None and now.utcoffset() == timedelta(0)
    assert clk.mission_day() == 96
    assert clk.scale == 60


def test_scale_60_one_real_second_is_one_mission_minute(clk, mono):
    before = clk.now()
    mono.t += 1
    assert clk.now() - before == timedelta(seconds=60)


def test_day_start_and_mission_day(clk):
    assert clk.day_start(1) == MISSION_START
    assert clk.day_start(96) == datetime(2027, 4, 15, tzinfo=UTC)
    assert clk.mission_day(datetime(2027, 1, 10, 23, 59, tzinfo=UTC)) == 1
    assert clk.mission_day(datetime(2027, 1, 11, tzinfo=UTC)) == 2


def test_day_rolls_over_at_midnight(clk, mono):
    mono.t += 17 * 3600 / 60  # 17 ore de misiune la ×60 → 00:00 a zilei 97
    assert clk.mission_day() == 97


def test_set_scale_does_not_jump(clk, mono):
    mono.t += 10
    before = clk.now()
    clk.set_scale(1)
    assert clk.now() == before
    mono.t += 5
    assert clk.now() - before == timedelta(seconds=5)
    assert clk.scale == 1


def test_jump_to_day_forward(clk):
    clk.jump_to_day(100, "09:30")
    assert clk.now() == clk.day_start(100) + timedelta(hours=9, minutes=30)
    assert clk.mission_day() == 100


@pytest.mark.parametrize("day", [96, 95, 1])
def test_jump_to_day_backwards_or_same_raises(clk, day):
    with pytest.raises(ValueError):
        clk.jump_to_day(day)


def test_real_seconds(clk):
    assert clk.real_seconds(700) == pytest.approx(700 / 60)


def test_freeze_until_next_start(clk, mono):
    at = datetime(2027, 4, 15, 12, 0, tzinfo=UTC)
    clk.freeze(at)
    mono.t += 3600
    assert clk.now() == at
    clk.start(mission_start=MISSION_START, day=96, time_hhmm="07:00", scale=60)
    mono.t += 1
    assert clk.now() == clk.day_start(96) + timedelta(hours=7, seconds=60)


def test_invalid_scale_raises(clk):
    with pytest.raises(ValueError):
        clk.set_scale(0)


def test_not_started_raises():
    with pytest.raises(RuntimeError):
        SimClock().now()
