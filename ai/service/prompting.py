"""Promptul trimis modelului: rolul (prompts/system.md) și cererea completată (prompts/answer.md)."""
from functools import lru_cache
from pathlib import Path

from rag.retrieve import Passage

from .schemas import AiServiceChatRequest

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
PASSAGE_WORDS = 160


@lru_cache(maxsize=4)
def template(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8").strip()


def shorten(text: str, words: int = PASSAGE_WORDS) -> str:
    parts = text.split()
    return text if len(parts) <= words else " ".join(parts[:words]) + " …"


def build_messages(body: AiServiceChatRequest, passages: list[Passage]) -> list[dict]:
    context = body.context
    rec = context.recommendation
    evidence = "\n".join(f"- {item.label}: {item.deviation_text}" for item in context.evidence) or "- (no measurements attached)"
    sources = "\n".join(f"[{number}] {passage.title}: {shorten(passage.text)}" for number, passage in enumerate(passages, 1))
    user = template("answer.md").format(
        mission_day=context.mission_day,
        environment=context.environment.replace("_", " "),
        alert=context.alert_title or "none (a general question)",
        evidence=evidence,
        recommendation_id=rec.id if rec else "none",
        level=rec.level if rec else "-",
        trigger=rec.trigger if rec else "-",
        action=rec.action if rec else "No catalog recommendation applies. If something worries you, notify the crew medical officer.",
        passages=sources or "(no relevant source found)",
        question=body.message,
    )
    history = [{"role": turn.role, "content": turn.content} for turn in body.history]
    return [{"role": "system", "content": template("system.md")}, *history, {"role": "user", "content": user}]
