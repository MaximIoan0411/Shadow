from app.engine.triage import decide
from app.engine.types import Finding


def finding(level: int, *, crew_id="cm-2", topic="immune", status=None, day=95, title="t") -> Finding:
    return Finding(
        crew_id=crew_id,
        topic=topic,
        level=level,
        status=status or ("alert" if level >= 2 else "watch"),
        title=title,
        explanation="e",
        evidence=(),
        recommendation_id=f"{topic}-{level}-1",
        day=day,
    )


def test_no_open_alert_creates():
    [d] = decide([finding(1)], {})
    assert d.action == "create" and d.alert_id is None and d.new_level is None


def test_open_alert_same_level_updates():
    [d] = decide([finding(2, title="new text")], {("cm-2", "immune"): ("al-0001", 2)})
    assert d.action == "update" and d.alert_id == "al-0001" and d.new_level == 2
    assert d.finding.title == "new text"


def test_level_never_goes_down():
    [d] = decide([finding(1)], {("cm-2", "immune"): ("al-0001", 3)})
    assert d.action == "update" and d.new_level == 3


def test_lower_open_alert_escalates():
    [d] = decide([finding(2)], {("cm-2", "immune"): ("al-0001", 1)})
    assert d.action == "escalate" and d.alert_id == "al-0001" and d.new_level == 2


def test_two_findings_same_subject_one_decision_most_severe():
    decisions = decide([finding(1, title="yellow"), finding(2, title="red")], {})
    assert len(decisions) == 1
    assert decisions[0].action == "create" and decisions[0].finding.title == "red"


def test_same_level_alert_beats_watch():
    [d] = decide([finding(1, status="alert", title="a"), finding(1, status="watch", title="w")], {})
    assert d.finding.title == "a"


def test_different_subjects_and_crew_are_separate():
    decisions = decide(
        [finding(1), finding(1, topic="behavioral"), finding(2, crew_id="cm-1")],
        {("cm-2", "behavioral"): ("al-0007", 1)},
    )
    assert [(d.finding.crew_id, d.finding.topic, d.action) for d in decisions] == [
        ("cm-2", "immune", "create"),
        ("cm-2", "behavioral", "update"),
        ("cm-1", "immune", "create"),
    ]


def test_no_findings_no_decisions():
    assert decide([], {("cm-2", "immune"): ("al-0001", 2)}) == []
