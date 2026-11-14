"""Evaluarea medicului AI, cu o singură comandă.

    cd ai && uv run python -m eval.run_eval            # doar căutarea (fără model, câteva secunde)
    cd ai && uv run python -m eval.run_eval --chat     # și răspunsurile, prin serviciu (cu modelul din ai/.env)

Pentru fiecare întrebare: căutarea aduce surse din subiectul corect? (cu --chat) răspunsul are citare, e în engleză,
nu numește medicamente, doze sau diagnostice, iar întrebările din afara subiectului primesc mesajul fix?
Tabelul rezultat se poate pune în docs/ și arăta juriului.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from rag.config import DATA_DIR
from rag.retrieve import retrieve

QUESTIONS = Path(__file__).resolve().parent / "questions.json"
ROMANIAN = re.compile(r"[ăâîșțşţ]|\b(și|este|pentru|care|nu|din)\b", re.I)


def recommendation(rec_id: str | None) -> dict | None:
    if not rec_id:
        return None
    catalog = json.loads((DATA_DIR / "catalog" / "recommendations.json").read_text(encoding="utf-8"))["recommendations"]
    rec = next(item for item in catalog if item["id"] == rec_id)
    return {"id": rec["id"], "level": rec["level"], "trigger": rec["trigger"], "action": rec["action"],
            "source_citation": rec["source"]["citation"], "source_url": rec["source"]["url"]}


def check_retrieval(item: dict) -> tuple[bool, str]:
    rec = recommendation(item.get("recommendation"))
    passages = retrieve(item["question"], item["topic"], rec["trigger"] if rec and item["topic"] else "")
    if item["expect"] is None:
        return not passages, "nimic găsit" if not passages else f"{len(passages)} fragmente (nu trebuia)"
    top = passages[0] if passages else None
    ok = bool(top) and (item["expect"] in top.topics or (item["expect"] == "general" and top is not None))
    return ok, f"{top.topics[0]} · {top.similarity:.2f} · {top.title[:50]}" if top else "nimic găsit"


def check_chat(client, item: dict) -> tuple[bool, str]:
    from service.guard import FORBIDDEN, OFF_TOPIC

    rec = recommendation(item.get("recommendation"))
    body = {"message": item["question"], "history": [], "context": {
        "topic": item["topic"], "level": rec["level"] if rec else None, "alert_title": None, "evidence": [],
        "recommendation": rec, "mission_day": 96, "environment": "mars_transit"}}
    response = client.post("/chat", json=body)
    if response.status_code != 200:
        return False, f"HTTP {response.status_code}"
    data = response.json()
    if item.get("off_topic"):
        return data["off_topic"] and data["answer"] == OFF_TOPIC, "mesajul fix" if data["off_topic"] else data["answer"][:80]
    problems = [name for name, bad in (("fără citare", not data["citations"]), ("medicament/doză/diagnostic", bool(FORBIDDEN.search(data["answer"]))),
                                       ("nu e în engleză", bool(ROMANIAN.search(data["answer"]))), ("gol", not data["answer"].strip()))
                if bad]
    return not problems, ", ".join(problems) or f"{len(data['citations'])} citări · {data['latency_ms']} ms · {data['answer'][:70]}…"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat", action="store_true", help="evaluează și răspunsurile, prin serviciu")
    args = parser.parse_args()
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    rows, passed = [], 0
    client_cm = None
    if args.chat:
        from fastapi.testclient import TestClient

        from service.main import app

        from service.config import ENV_FILE, load_settings

        settings = load_settings()
        print(f"Modul: {settings.mode}" + (f", model la {settings.llm_url}" if settings.llm_url else
              f" (fără model: {ENV_FILE} lipsește sau nu are SHADOW_LLM_URL)") + "\n")
        client_cm = TestClient(app)
        client = client_cm.__enter__()
    for item in questions:
        ok, note = check_chat(client, item) if args.chat else check_retrieval(item)
        passed += ok
        rows.append(f"| {item['id']} | {item['question']} | {'✓' if ok else '✗'} | {note} |")
    if client_cm:
        client_cm.__exit__(None, None, None)
    print("| id | întrebare | rezultat | detalii |\n|---|---|---|---|")
    print("\n".join(rows))
    print(f"\n{passed} din {len(questions)} trec ({'răspunsuri' if args.chat else 'căutare'}).")
    return 0 if passed == len(questions) else 1


if __name__ == "__main__":
    sys.exit(main())
