"""Triajul: din constatări + alertele deschise → ce se creează, se actualizează sau se escaladează. TASK T15."""
from .types import Finding, TriageDecision


def decide(findings: list[Finding], open_alerts: dict[tuple[str, str], tuple[str, int]]) -> list[TriageDecision]:
    """`open_alerts`: (crew_id, topic) → (alert_id, level). Reguli:
    - nicio alertă deschisă pe subiect → create;
    - există, același nivel sau mai mic → update (nivelul NU coboară);
    - există, nivel mai mare → escalate cu new_level."""
    raise NotImplementedError("T15")
