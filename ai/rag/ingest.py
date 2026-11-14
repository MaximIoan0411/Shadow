"""Reface indexul bazei de cunoștințe: taie documentele în fragmente, le calculează vectorii, salvează în index/.

    cd ai && uv run python -m rag.ingest

Fără internet, după ce modelul de embedding a fost descărcat o dată (stă în models/embeddings/).

Fragmentele vin din două locuri:
  * documentele oficiale din corpus/docs/ (descărcate cu `python -m rag.fetch`), textul original, în engleză;
  * datele echipei din data/: pragurile din parameters.json, recomandările din catalog și funcțiile zonelor
    corpului; fiecare cu sursa ei.
"""
import json
import re
import sys
import time

import numpy as np

from .config import CHUNK_MIN_WORDS, CHUNK_OVERLAP, CHUNK_WORDS, DATA_DIR, EMBED_MODEL, INDEX_DIR, SOURCES_FILE, CORPUS_DIR
from .embed import embed_passages

# subiectele din parameters.json (chei în română) → subiectele din contract
PARAM_TOPIC = {"comportamental": "behavioral", "cardiovascular": "cardio", "imunitar": "immune",
               "oase_muschi": "musculoskeletal", "radiatii": "radiation", "comunicare": "general"}
# un fragment cu prea multe ani / „et al.” / doi e o listă de bibliografie, nu text
CITATION_MARK = re.compile(r"\b(?:19|20)\d{2}\b|et al\.|doi|\bVol\.|\bpp?\.\s*\d")
MAX_CITATION_DENSITY = 0.07
TITLE_CHARS = 160


def short(text: str, limit: int = TITLE_CHARS) -> str:
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def windows(words: list[str]) -> list[list[str]]:
    step = CHUNK_WORDS - CHUNK_OVERLAP
    return [words[start:start + CHUNK_WORDS] for start in range(0, max(len(words) - CHUNK_OVERLAP, 1), step)]


def document_chunks() -> list[dict]:
    if not SOURCES_FILE.exists():
        print("  corpus/sources.json lipsește: rulați întâi `python -m rag.fetch`", file=sys.stderr)
        return []
    chunks = []
    for doc in json.loads(SOURCES_FILE.read_text(encoding="utf-8"))["documents"]:
        words = (CORPUS_DIR / doc["file"]).read_text(encoding="utf-8").split()
        for position, part in enumerate(windows(words)):
            text = " ".join(part)
            if len(part) < CHUNK_MIN_WORDS or len(CITATION_MARK.findall(text)) / len(part) > MAX_CITATION_DENSITY:
                continue
            chunks.append({"doc": doc["id"], "title": doc["title"], "url": doc["url"], "topics": doc["topics"],
                           "kind": "official", "position": position, "text": text})
    return chunks


def value_text(value) -> str:
    if isinstance(value, (int, float)):
        return f"{value:g}"
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def data_chunks() -> list[dict]:
    chunks = []
    params = json.loads((DATA_DIR / "parameters.json").read_text(encoding="utf-8"))
    for key, pillar in params["piloni"].items():
        for param in pillar["parametri"]:
            source = param["sursa"]
            url = source.get("url") or (f"https://doi.org/{source['doi']}" if source.get("doi") else "")
            status = "" if param["status"] == "VERIFICAT" else " (not verified against the source)"
            text = f"{param['nume']}: {value_text(param['valoare'])} {param['unitate']}. {param['explicatie']}{status}"
            chunks.append({"doc": f"param:{param['id']}", "title": short(source["citare"]), "url": url,
                           "topics": [PARAM_TOPIC.get(key, "general")], "kind": "team", "position": 0, "text": text})
    catalog = json.loads((DATA_DIR / "catalog" / "recommendations.json").read_text(encoding="utf-8"))
    for rec in catalog["recommendations"]:
        steps = " ".join(rec.get("steps") or [])
        text = f"Recommendation {rec['id']} (level {rec['level']}). When: {rec['trigger']} What to do: {rec['action']} Steps: {steps}"
        chunks.append({"doc": f"rec:{rec['id']}", "title": short(rec["source"]["citation"]), "url": rec["source"]["url"],
                       "topics": [rec["topic"]], "kind": "team", "position": 0, "text": text})
    body = json.loads((DATA_DIR / "texts" / "body_functions.json").read_text(encoding="utf-8"))
    for zone in body["pillars"]:
        source = (zone.get("sources") or [{}])[0]
        text = f"{zone['function_text']} {zone['hazard_text']} Limits: {zone['limits_text']}"
        chunks.append({"doc": f"body:{zone['pillar']}", "title": short(source.get("citation", "SHADOW team")),
                       "url": source.get("url", ""), "topics": [zone["pillar"]], "kind": "team", "position": 0, "text": text})
    return [chunk for chunk in chunks if chunk["url"]]


def main() -> int:
    started = time.time()
    chunks = document_chunks() + data_chunks()
    if not chunks:
        print("Nimic de indexat.", file=sys.stderr)
        return 1
    for number, chunk in enumerate(chunks):
        chunk["id"] = number
    vectors = embed_passages([chunk["text"] for chunk in chunks])
    INDEX_DIR.mkdir(exist_ok=True)
    np.save(INDEX_DIR / "vectors.npy", vectors)
    (INDEX_DIR / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
    documents = sorted({chunk["doc"] for chunk in chunks if chunk["kind"] == "official"})
    meta = {"model": EMBED_MODEL, "chunks": len(chunks), "documents": len(documents),
            "team_entries": sum(1 for chunk in chunks if chunk["kind"] == "team"), "built": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (INDEX_DIR / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"Index: {meta['chunks']} fragmente ({meta['documents']} documente oficiale + {meta['team_entries']} intrări din data/), "
          f"{time.time() - started:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
