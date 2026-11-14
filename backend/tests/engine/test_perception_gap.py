import pytest

from app.engine.derived import PERCEPTION_GAP_ALERT, PERCEPTION_GAP_WATCH
from app.engine.perception_gap import compute


def test_feels_fine_but_data_say_otherwise_is_alert():
    self_score, objective, gap, status, text, signals = compute(
        4,
        {"keystrokes": 30.0, "night_pulse": 58.0, "sleep": 72.5},
        {"keystrokes": "Typing: -18% speed", "night_pulse": "Night pulse: +7.0 bpm", "sleep": "Sleep: -1.1 h"},
    )
    assert self_score == 80 and objective == pytest.approx(53.5, abs=0.1)
    assert gap >= PERCEPTION_GAP_ALERT and status == "alert"
    assert signals == ["Typing: -18% speed", "Night pulse: +7.0 bpm", "Sleep: -1.1 h"]
    assert text == (
        "You rate yourself 4/5 (80/100), but your objective data score 54/100 only "
        "(Typing: -18% speed, Night pulse: +7.0 bpm, Sleep: -1.1 h)."
    )


def test_watch_between_thresholds():
    *_, gap, status, _text, _signals = compute(4, {"night_pulse": 80 - PERCEPTION_GAP_WATCH})
    assert gap == PERCEPTION_GAP_WATCH and status == "watch"


def test_agreement_is_ok():
    _s, objective, gap, status, text, signals = compute(4, {"night_pulse": 86.0, "sleep": 88.0})
    assert objective == 87 and gap == -7 and status == "ok" and signals == []
    assert text.endswith("they agree.")


def test_slightly_lower_than_feeling_names_the_causes():
    *_, gap, status, text, _signals = compute(
        4, {"night_pulse": 58.0, "sleep": 72.4}, {"night_pulse": "Night pulse: +7.0 bpm", "sleep": "Sleep: -1.1 h"}
    )
    assert status == "ok" and 7.5 < gap < 15
    assert "a little lower than how you feel (Night pulse: +7.0 bpm, Sleep: -1.1 h)." in text


def test_feeling_worse_than_data_is_ok():
    *_, gap, status, text, _signals = compute(1, {"night_pulse": 100.0})
    assert gap == -80 and status == "ok" and "better than you feel" in text


def test_missing_scores_are_left_out():
    _s, objective, *_ = compute(4, {"night_pulse": 60.0, "keystrokes": None})
    assert objective == 60


def test_unknown_without_mood_or_scores():
    assert compute(None, {"night_pulse": 60.0})[3] == "unknown"
    _s, objective, gap, status, *_ = compute(4, {})
    assert objective is None and gap is None and status == "unknown"
