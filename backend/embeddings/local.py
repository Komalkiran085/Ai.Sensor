"""Local embedder — runs entirely on this machine via sentence-transformers, no API
key, no per-call cost, no regulation/query text ever leaves the plant's own infra.

Model: BAAI/bge-small-en-v1.5 (384-dim, ~130MB). Chosen over the more commonly-used
all-MiniLM-L6-v2 because it's trained specifically for asymmetric retrieval (short
query -> longer passage, exactly this use case) and scores higher on retrieval
benchmarks while staying small enough for comfortable CPU-only inference — no GPU
needed for the handful of regulation clauses and queries this agent handles.

BGE's documented convention: prefix the QUERY (not the passage) with an instruction
string for meaningfully better retrieval quality. See the model card on HuggingFace.
"""
from __future__ import annotations
import logging

from embeddings.base import Embedder

logger = logging.getLogger(__name__)

MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIMENSION = 384
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class LocalEmbedder(Embedder):
    dimension = DIMENSION

    def __init__(self):
        self._model = None

    def _load(self):
        if self._model is None:
            logger.info("Loading local embedding model %s (first call only)...", MODEL_NAME)
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(MODEL_NAME)
            logger.info("Embedding model loaded.")
        return self._model

    def embed_query(self, text: str) -> list[float]:
        model = self._load()
        vec = model.encode(QUERY_INSTRUCTION + text, normalize_embeddings=True)
        return vec.tolist()

    def embed_passage(self, text: str) -> list[float]:
        model = self._load()
        vec = model.encode(text, normalize_embeddings=True)
        return vec.tolist()
