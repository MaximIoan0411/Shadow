import pytest

from app.datafiles import load_all
from app.engine.derived import KEYSTROKE_ALERT_FATIGUE, KEYSTROKE_WATCH_FATIGUE, MIN_SPREAD
from app.engine.pillars import behavioral as b
from app.engine.pillars.behavioral import KeyEventIn
from app.simulator.scenario import generate


def typing(n: int, *, flight: float = 200.0, hold: float = 90.0, start: float = 1000.0, backspace_every: int = 0):
    return [
        KeyEventIn(
            t_down_ms=start + i * flight,
            t_up_ms=start + i * flight + hold,
            key_class="backspace" if backspace_every and i % backspace_every == 0 else "char",
        )
        for i in range(n)
    ]


def baseline(kpm=214.0, hold=96.0, sessions=7) -> dict:
    flight = 60000 / kpm
    one = {
        "hold_ms_mean": hold,
        "hold_ms_sd": hold * 0.2,
        "flight_ms_mean": flight,
        "flight_ms_sd": flight * 0.35,
        "backspace_rate": 0.05,
        "keys_per_min": kpm,
        "n_keys": 400,
    }
    return b.typing_baseline([one] * sessions, min_sessions=7)


def test_features_of_a_steady_session():
    f = b.accumulate({}, typing(101, flight=200, hold=90, backspace_every=10))
    assert f["n_keys"] == 101 and f["flight_n"] == 100
    assert f["hold_ms_mean"] == pytest.approx(90) and f["hold_ms_sd"] == pytest.approx(0, abs=1e-6)
    assert f["flight_ms_mean"] == pytest.approx(200)
    assert f["keys_per_min"] == pytest.approx(300)
    assert f["backspace_rate"] == pytest.approx(11 / 101)
    assert f["active_ms"] == pytest.approx(20000)


def test_two_batches_equal_one_batch():
    events = typing(60, flight=180, hold=85) + typing(40, flight=260, hold=120, start=1000 + 60 * 180)
    whole = b.accumulate({}, events)
    first = b.accumulate({}, events[:37])
    both = b.accumulate(first, events[37:])
    for key in (*b.ACCUMULATORS, *b.FEATURES, "last_down_ms"):
        assert both[key] == pytest.approx(whole[key]), key


def test_events_inside_a_batch_can_arrive_unordered():
    events = typing(20)
    assert b.accumulate({}, list(reversed(events))) == b.accumulate({}, events)


def test_five_second_pause_is_not_flight_time():
    before, after = typing(10, flight=200), typing(10, flight=200, start=1000 + 9 * 200 + 5000)
    f = b.accumulate({}, before + after)
    assert f["n_keys"] == 20 and f["flight_n"] == 18
    assert f["flight_ms_mean"] == pytest.approx(200)
    assert f["active_ms"] == pytest.approx(18 * 200)
    assert f["keys_per_min"] == pytest.approx(300)


def test_timer_reset_between_batches_is_skipped():
    first = b.accumulate({}, typing(10, start=50_000))
    f = b.accumulate(first, typing(10, start=100))
    assert f["flight_n"] == 18 and f["flight_ms_mean"] == pytest.approx(200)


def test_baseline_mean_and_minimum_spread():
    base = baseline()
    assert base["ready"] and base["sessions"] == 7 and base["n_keys"] == 2800
    assert base["mean"]["keys_per_min"] == 214
    assert base["sd"]["keys_per_min"] == MIN_SPREAD["keys_per_min"]
    assert base["sd"]["hold_ms_mean"] == MIN_SPREAD["hold_ms_mean"]
    assert not baseline(sessions=6)["ready"]


def test_same_as_baseline_gives_zero():
    base = baseline()
    index, z = b.fatigue_index(base["mean"], base)
    assert index == 0 and set(z) == {"hold_ms_mean", "keys_per_min", "flight_ms_mean", "backspace_rate"}
    assert all(v == 0 for v in z.values())


def test_faster_typing_is_not_fatigue():
    base = baseline()
    fast = {**base["mean"], "keys_per_min": 260.0, "flight_ms_mean": 60000 / 260, "hold_ms_mean": 80.0}
    index, z = b.fatigue_index(fast, base)
    assert index == 0 and z["keys_per_min"] > 0 and z["hold_ms_mean"] < 0


def test_twenty_percent_slower_session_is_clearly_more_fatigued():
    base = baseline()
    normal = {**base["mean"], "keys_per_min": 214 * 0.98, "flight_ms_mean": 60000 / (214 * 0.98)}
    slow = {**base["mean"], "keys_per_min": 214 * 0.8, "flight_ms_mean": 60000 / (214 * 0.8), "hold_ms_mean": 96 * 1.2}
    normal_index, _ = b.fatigue_index(normal, base)
    slow_index, z = b.fatigue_index(slow, base)
    assert normal_index < 15
    assert slow_index >= KEYSTROKE_WATCH_FATIGUE and slow_index > normal_index + 40
    assert z["keys_per_min"] < -4 and z["hold_ms_mean"] > 3


def test_status_thresholds():
    assert b.status_for(None) == "unknown"
    assert b.status_for(KEYSTROKE_WATCH_FATIGUE - 0.1) == "ok"
    assert b.status_for(KEYSTROKE_WATCH_FATIGUE) == "watch"
    assert b.status_for(KEYSTROKE_ALERT_FATIGUE) == "alert"


def test_typing_finding():
    base = baseline()
    slow = {**base["mean"], "keys_per_min": 175.5, "flight_ms_mean": 60000 / 175.5, "hold_ms_mean": 112.3}
    fatigue, _ = b.fatigue_index(slow, base)
    f = b.typing_finding("cm-2", slow, base, fatigue, day=95)
    assert f.topic == "behavioral" and f.level == 1 and f.recommendation_id == "behavioral-1-1"
    assert f.title == "Typing 18% slower than usual"
    assert [e.metric_key for e in f.evidence] == ["keys_per_min", "hold_ms_mean"]
    assert f.evidence[0].deviation_text == "-18% vs your baseline" and f.evidence[0].baseline == 214
    assert b.typing_finding("cm-2", base["mean"], base, 10.0, day=95) is None
    assert b.typing_finding("cm-2", base["mean"], base, None, day=95) is None


def test_score():
    assert b.score(None, None).status == "unknown" and b.score(None, None).score is None
    assert b.score(10.0, None).score == 90 and b.score(10.0, None).status == "ok"
    watch = b.score(68.0, None)
    assert watch.score == 32 and watch.status == "watch" and "68/100" in watch.headline
    assert b.score(68.0, -1.0).score == pytest.approx((32 + 80) / 2)


def test_scenario_calibration():
    """cm-2's slowdown (days 95-97) is a watch; the crew-wide poor sleep (days 40-41) and normal days are not."""
    scenario = load_all().scenario
    days = generate(scenario, from_day=1, to_day=97)
    for crew in scenario.crew_baselines:
        mine = [d for d in days if d.crew_id == crew]
        base = b.typing_baseline([d.keystroke for d in mine if d.day <= 7], min_sessions=7)
        index = {d.day: b.fatigue_index(d.keystroke, base)[0] for d in mine if d.day > 7}
        for day, value in index.items():
            slowdown = crew == "cm-2" and 95 <= day <= 97
            assert (b.status_for(value) == "watch") == slowdown, (crew, day, value)
