"""Tipurile motorului (separate de tabele și de contract). Gata, nu e un task."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

Status = Literal["ok", "watch", "alert", "unknown"]
Topic = Literal["behavioral", "cardio", "immune", "musculoskeletal", "radiation", "cross_signal"]


@dataclass(frozen=True)
class Point:
    day: int
    t: datetime
    value: float


@dataclass(frozen=True)
class Baseline:
    median: float
    spread: float          # deviația standard robustă (1.4826 × MAD), minimum `min_spread`
    n: int
    ready: bool            # n >= min_n

    @property
    def band(self) -> tuple[float, float]:
        return (self.median - self.spread, self.median + self.spread)


@dataclass(frozen=True)
class EvidenceItem:
    metric_key: str
    label: str
    value: float | None
    unit: str
    baseline: float | None
    deviation_text: str    # în română, ex. "+7 bpm peste mediana personală, 3 nopți"


@dataclass(frozen=True)
class Finding:
    """Rezultatul unei reguli. Triajul (T15) îl transformă în alertă nouă sau actualizare."""
    crew_id: str
    topic: Topic
    level: int             # 1..3
    status: Status         # watch | alert
    title: str             # în română, gata de afișat
    explanation: str
    evidence: tuple[EvidenceItem, ...]
    recommendation_id: str
    day: int
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PillarScore:
    score: float | None    # 0..100; 100 = ca baseline-ul
    status: Status
    headline: str          # în română


@dataclass(frozen=True)
class TriageDecision:
    """Ce trebuie făcut în bază pentru o constatare."""
    action: Literal["create", "update", "escalate", "none"]
    finding: Finding
    alert_id: str | None = None      # pentru update / escalate
    new_level: int | None = None
