"""Căutarea în baza de cunoștințe: pentru o întrebare, cele mai potrivite 3–4 fragmente, cu titlu și URL.

Două căutări, unite: după sens (vectorii) și după cuvinte (BM25, prinde termenii exacți: „PVT-B”, „ARED”, „SEP”).
Fragmentele din subiectul alertei primesc un mic avantaj. Sub un prag de asemănare nu se întoarce nimic: mai bine
„fără sursă” decât o sursă nepotrivită.
"""
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from .config import INDEX_DIR
from .embed import embed_query

TOP_K = 4
PER_DOCUMENT = 2
RRF_K = 60
TOPIC_BOOST = 1.35
# sub această asemănare (cosinus) fragmentul nu e considerat relevant; reglat pe ai/eval/retrieval.json
MIN_SIMILARITY = 0.6
BM25_K1 = 1.4
BM25_B = 0.75
CANDIDATES = 40
WORD = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
STOP = frozenset("a an the and or of to in on for with by at from is are was were be been it its this that these those as "
                 "my me i you your we our do does did can could should would what why how when which who whom there their "
                 "not no if so than then into about after before over under up down out more most less very just".split())

# cuvinte de căutare pentru fiecare subiect (completează întrebările scurte, de tipul „ce fac acum?”)
TOPIC_WORDS = {
    "behavioral": "sleep fatigue alertness typing reaction time vigilance PVT behavioral health",
    "cardio": "heart rate blood pressure cardiovascular orthostatic aerobic fitness",
    "immune": "immune infection viral reactivation night heart rate temperature symptoms",
    "musculoskeletal": "bone density muscle strength loading exercise ARED",
    "radiation": "radiation solar particle event shelter dose dosimeter",
    "cross_signal": "crew environment cabin sleep stress",
}


@dataclass(frozen=True)
class Passage:
    title: str
    url: str
    text: str
    similarity: float
    topics: tuple[str, ...]
    kind: str


def tokens(text: str) -> list[str]:
    return [word for word in WORD.findall(text.lower()) if word not in STOP and len(word) > 1]


class Index:
    def __init__(self) -> None:
        self.chunks: list[dict] = json.loads((INDEX_DIR / "chunks.json").read_text(encoding="utf-8"))
        self.vectors: np.ndarray = np.load(INDEX_DIR / "vectors.npy")
        self.documents = len({chunk["doc"] for chunk in self.chunks if chunk["kind"] == "official"})
        docs = [Counter(tokens(chunk["text"] + " " + chunk["title"])) for chunk in self.chunks]
        self.lengths = np.array([sum(doc.values()) for doc in docs], dtype=np.float32)
        self.average = float(self.lengths.mean())
        self.postings: dict[str, list[tuple[int, int]]] = {}
        for number, doc in enumerate(docs):
            for word, count in doc.items():
                self.postings.setdefault(word, []).append((number, count))
        self.idf = {word: math.log(1 + (len(docs) - len(hits) + 0.5) / (len(hits) + 0.5)) for word, hits in self.postings.items()}

    def bm25(self, query: str) -> np.ndarray:
        scores = np.zeros(len(self.chunks), dtype=np.float32)
        for word in set(tokens(query)):
            for number, count in self.postings.get(word, []):
                norm = BM25_K1 * (1 - BM25_B + BM25_B * self.lengths[number] / self.average)
                scores[number] += self.idf[word] * count * (BM25_K1 + 1) / (count + norm)
        return scores


@lru_cache(maxsize=1)
def load_index() -> Index:
    return Index()


def index_ready() -> bool:
    return (INDEX_DIR / "chunks.json").exists() and (INDEX_DIR / "vectors.npy").exists()


def retrieve(question: str, topic: str | None = None, hint: str = "", k: int = TOP_K) -> list[Passage]:
    """Fragmentele cele mai relevante. `hint` = titlul alertei și declanșatorul recomandării, de la backend."""
    index = load_index()
    dense = index.vectors @ embed_query(f"{question} {hint}".strip())
    lexical = index.bm25(f"{question} {hint} {TOPIC_WORDS.get(topic or '', '')}")
    dense_rank = {number: rank for rank, number in enumerate(np.argsort(-dense)[:CANDIDATES])}
    lexical_rank = {number: rank for rank, number in enumerate(np.argsort(-lexical)[:CANDIDATES]) if lexical[number] > 0}
    fused: dict[int, float] = {}
    for ranks in (dense_rank, lexical_rank):
        for number, rank in ranks.items():
            fused[number] = fused.get(number, 0.0) + 1 / (RRF_K + rank)
    for number in fused:
        if topic and topic in index.chunks[number]["topics"]:
            fused[number] *= TOPIC_BOOST
    picked: list[Passage] = []
    per_doc: Counter = Counter()
    for number in sorted(fused, key=fused.get, reverse=True):
        chunk = index.chunks[number]
        if dense[number] < MIN_SIMILARITY or per_doc[chunk["doc"]] >= PER_DOCUMENT:
            continue
        per_doc[chunk["doc"]] += 1
        picked.append(Passage(chunk["title"], chunk["url"], chunk["text"], float(dense[number]), tuple(chunk["topics"]), chunk["kind"]))
        if len(picked) == k:
            break
    return picked
