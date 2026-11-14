"""Vectorii textelor, cu un model mic rulat local (fastembed, ONNX, fără placă video)."""
from functools import lru_cache

import numpy as np

from .config import EMBED_CACHE, EMBED_MODEL, QUERY_PREFIX


@lru_cache(maxsize=1)
def _model():
    from fastembed import TextEmbedding

    # după prima descărcare modelul stă în ai/models/embeddings și merge fără internet
    return TextEmbedding(EMBED_MODEL, cache_dir=str(EMBED_CACHE))


def embed_passages(texts: list[str]) -> np.ndarray:
    vectors = np.array(list(_model().embed(texts, batch_size=32)), dtype=np.float32)
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def embed_query(text: str) -> np.ndarray:
    vector = np.array(next(iter(_model().embed([QUERY_PREFIX + text]))), dtype=np.float32)
    return vector / np.linalg.norm(vector)
