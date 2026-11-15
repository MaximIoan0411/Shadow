"""Promptul trimis modelului: rolul (prompts/system.md) și cererea completată: prompts/answer.md pentru o întrebare
despre o alertă, prompts/general.md pentru o întrebare generală (cu alertele deschise și zonele de pe corp)."""
from functools import lru_cache
from pathlib import Path

from rag.retrieve import Passage

from .schemas import AiContext, AiServiceChatRequest

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
PASSAGE_WORDS = 160
GENERAL = "general"
OTHER_SUBJECT = "- (not related to this question: answer it from the numbered sources)"
ZONE_STATUS = {"ok": "within normal", "watch": "to watch", "alert": "alert", "unknown": "no data"}


@lru_cache(maxsize=4)
def template(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8").strip()


def shorten(text: str, words: int = PASSAGE_WORDS) -> str:
    parts = text.split()
    return text if len(parts) <= words else " ".join(parts[:words]) + " …"


def alert_prompt(context: AiContext, sources: str, question: str) -> str:
    rec = context.recommendation
    evidence = "\n".join(f"- {item.label}: {item.deviation_text}" for item in context.evidence) or "- (no measurements attached)"
    return template("answer.md").format(
        mission_day=context.mission_day,
        environment=context.environment.replace("_", " "),
        alert=context.alert_title or "none (a general question)",
        evidence=evidence,
        recommendation_id=rec.id if rec else "none",
        level=rec.level if rec else "-",
        trigger=rec.trigger if rec else "-",
        action=rec.action if rec else "No catalog recommendation applies. If something worries you, notify the crew medical officer.",
        passages=sources,
        question=question,
    )


def related_to_question(context: AiContext, passages: list[Passage]) -> bool:
    """False when the sources found are clearly about another subject than every open alert (a solar storm question
    while the alerts are about pulse and typing): the alerts would only pull the answer off topic."""
    found = {topic for passage in passages for topic in passage.topics if topic != GENERAL}
    return not found or bool(found & {alert.topic for alert in context.open_alerts})


def general_prompt(context: AiContext, sources: str, question: str, passages: list[Passage]) -> str:
    if context.open_alerts and not related_to_question(context, passages):
        return template("general.md").format(
            mission_day=context.mission_day,
            environment=context.environment.replace("_", " "),
            passages=sources,
            open_alerts=OTHER_SUBJECT,
            zones=OTHER_SUBJECT,
            question=question,
        )
    open_alerts = "\n".join(
        f"- Level {alert.level}: {alert.title}. Observed: {'; '.join(alert.observed) or 'see the alert'}. "
        f"What the catalog says to do: {alert.action}"
        for alert in context.open_alerts
    )
    zones = "\n".join(f"- {zone.name}: {ZONE_STATUS[zone.status]} ({zone.headline})" for zone in context.zones)
    return template("general.md").format(
        mission_day=context.mission_day,
        environment=context.environment.replace("_", " "),
        passages=sources,
        open_alerts=open_alerts or "- none: no open alert",
        zones=zones or "- (not available)",
        question=question,
    )


def build_messages(body: AiServiceChatRequest, passages: list[Passage]) -> list[dict]:
    context = body.context
    sources = "\n".join(f"[{number}] {passage.title}: {shorten(passage.text)}" for number, passage in enumerate(passages, 1))
    sources = sources or "(no relevant source found)"
    general = context.topic is None and context.recommendation is None
    user = general_prompt(context, sources, body.message, passages) if general else alert_prompt(context, sources, body.message)
    history = [{"role": turn.role, "content": turn.content} for turn in body.history]
    return [{"role": "system", "content": template("system.md")}, *history, {"role": "user", "content": user}]
