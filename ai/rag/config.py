"""Căile și setările bazei de cunoștințe, într-un singur loc."""
import os
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = AI_ROOT.parent
DATA_DIR = REPO_ROOT / "data"
CORPUS_DIR = AI_ROOT / "corpus"
DOCS_DIR = CORPUS_DIR / "docs"
CATALOG_FILE = CORPUS_DIR / "catalog.json"
SOURCES_FILE = CORPUS_DIR / "sources.json"
# SHADOW_INDEX_DIR: alt folder pentru index (verificările de contract îl trimit spre unul gol)
INDEX_DIR = Path(os.environ.get("SHADOW_INDEX_DIR") or AI_ROOT / "index")
EMBED_CACHE = AI_ROOT / "models" / "embeddings"

# Model mic, rulat local pe procesor (≈65 MB). Textele și interfața sunt în engleză.
EMBED_MODEL = os.environ.get("SHADOW_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
# bge cere un prefix pe întrebări (nu și pe fragmente) pentru căutare
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# fragmentele: 150–300 de cuvinte, cu puțină suprapunere
CHUNK_WORDS = 220
CHUNK_OVERLAP = 40
CHUNK_MIN_WORDS = 40
