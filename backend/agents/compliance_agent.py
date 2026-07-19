"""Compliance Agent — the retrieval step of the pipeline: looks up actual regulation
text relevant to what's happening in this zone, instead of an LLM guessing OISD/DGMS/
Factory Act clause numbers from memory.

Retrieval is real semantic vector search (pgvector cosine distance) via an injected
Embedder — see embeddings/base.py and embeddings/local.py for the default local model.
Falls back to keyword matching if no embedder is configured, or if vector search fails
for any reason (e.g. the embedding column isn't populated yet) — so the agent degrades
gracefully rather than going silent.
"""
from __future__ import annotations
import asyncio
import logging
import re

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Regulation
from embeddings.base import Embedder

logger = logging.getLogger(__name__)

_STOPWORDS = {"the", "a", "an", "in", "of", "to", "and", "or", "for", "is", "on", "at", "safety", "conditions", "readings"}


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


class ComplianceAgent:
    def __init__(self, embedder: Embedder | None = None):
        self.embedder = embedder

    async def assess(self, session: AsyncSession, pack: str, query_text: str, top_k: int = 3) -> dict:
        if not query_text:
            return {"agent": "compliance", "score": 0.0, "details": [], "citations": [], "retrieval": "none"}

        matches: list[Regulation] | None = None
        retrieval = "vector"
        if self.embedder:
            try:
                matches = await self._vector_search(session, pack, query_text, top_k)
            except Exception:
                logger.exception("Vector search failed, falling back to keyword match")
                matches = None

        if matches is None:
            retrieval = "keyword"
            matches = await self._keyword_search(session, pack, query_text, top_k)

        citations = [{"source": m.source, "clause_ref": m.clause_ref, "content": m.content} for m in matches]
        details = [f"{c['clause_ref']}: {c['content'][:90]}…" for c in citations]

        # A matching clause is itself informative — there's a documented rule this
        # situation may be brushing up against — a small, bounded score bump, not a verdict.
        score = 0.2 if citations else 0.0
        return {"agent": "compliance", "score": score, "details": details, "citations": citations, "retrieval": retrieval}

    async def _vector_search(self, session: AsyncSession, pack: str, query_text: str, top_k: int) -> list[Regulation]:
        query_vec = await asyncio.to_thread(self.embedder.embed_query, query_text)
        result = await session.execute(
            select(Regulation)
            .where(Regulation.pack == pack, Regulation.embedding.is_not(None))
            .order_by(Regulation.embedding.cosine_distance(query_vec))
            .limit(top_k)
        )
        return list(result.scalars().all())

    async def _keyword_search(self, session: AsyncSession, pack: str, query_text: str, top_k: int) -> list[Regulation]:
        terms = _keywords(query_text)
        if not terms:
            return []
        conditions = [Regulation.content.ilike(f"%{t}%") for t in terms]
        result = await session.execute(
            select(Regulation).where(Regulation.pack == pack, or_(*conditions)).limit(top_k)
        )
        return list(result.scalars().all())
