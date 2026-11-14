from .types import Finding, TriageDecision

STATUS_RANK = {"unknown": 0, "ok": 1, "watch": 2, "alert": 3}


def _severity(f: Finding) -> tuple[int, int, int]:
    return (f.level, STATUS_RANK.get(f.status, 0), f.day)


def _most_severe(findings: list[Finding]) -> dict[tuple[str, str], Finding]:
    worst: dict[tuple[str, str], Finding] = {}
    for f in findings:
        key = (f.crew_id, f.topic)
        if key not in worst or _severity(f) > _severity(worst[key]):
            worst[key] = f
    return worst


def decide(findings: list[Finding], open_alerts: dict[tuple[str, str], tuple[str, int]]) -> list[TriageDecision]:
    """One decision per (crew_id, topic), from the most severe finding:
    no open alert → create; open at the same or a higher level → update (the level never goes down);
    open at a lower level → escalate to the finding's level."""
    decisions: list[TriageDecision] = []
    for key, finding in _most_severe(findings).items():
        if key not in open_alerts:
            decisions.append(TriageDecision(action="create", finding=finding))
            continue
        alert_id, level = open_alerts[key]
        if finding.level > level:
            decisions.append(
                TriageDecision(action="escalate", finding=finding, alert_id=alert_id, new_level=finding.level)
            )
        else:
            decisions.append(TriageDecision(action="update", finding=finding, alert_id=alert_id, new_level=level))
    return decisions
