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

# Cosine distance beyond which a regulation "match" isn't actually close enough to
# surface as a precaution — mirrors incident_agent.py's SIMILARITY_CUTOFF exactly, same
# reasoning: only vector search gives a distance worth gating on; a keyword-fallback hit
# has no ranking, so it never counts as precaution-eligible, only as a citation.
COMPLIANCE_SIMILARITY_CUTOFF = 0.5


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


class ComplianceAgent:
    def __init__(self, embedder: Embedder | None = None):
        self.embedder = embedder

    async def assess(self, session: AsyncSession, pack: str, query_text: str, top_k: int = 3) -> dict:
        if not query_text:
            return {"agent": "compliance", "score": 0.0, "details": [], "citations": [], "retrieval": "none"}

        matches: list[tuple[Regulation, float | None]] | None = None
        retrieval = "vector"
        if self.embedder:
            try:
                matches = await self._vector_search(session, pack, query_text, top_k)
            except Exception:
                logger.exception("Vector search failed, falling back to keyword match")
                matches = None

        if matches is None:
            retrieval = "keyword"
            matches = [(m, None) for m in await self._keyword_search(session, pack, query_text, top_k)]

        citations = []
        for m, dist in matches:
            # Only a real vector-search distance under cutoff earns "precaution" status —
            # a keyword hit (dist is None) or a weak vector match still cites the clause,
            # it just never claims the elevated confidence a precaution implies.
            eligible = retrieval == "vector" and dist is not None and dist < COMPLIANCE_SIMILARITY_CUTOFF
            citations.append({
                "source": m.source, "clause_ref": m.clause_ref, "content": m.content,
                "distance": dist, "precaution_eligible": eligible,
            })
        details = [f"{c['clause_ref']}: {c['content'][:90]}…" for c in citations]

        # A matching clause is itself informative — there's a documented rule this
        # situation may be brushing up against — a small, bounded score bump, not a verdict.
        score = 0.2 if citations else 0.0
        return {"agent": "compliance", "score": score, "details": details, "citations": citations, "retrieval": retrieval}

    async def _vector_search(self, session: AsyncSession, pack: str, query_text: str, top_k: int) -> list[tuple[Regulation, float]]:
        query_vec = await asyncio.to_thread(self.embedder.embed_query, query_text)
        result = await session.execute(
            select(Regulation, Regulation.embedding.cosine_distance(query_vec).label("dist"))
            .where(Regulation.pack == pack, Regulation.embedding.is_not(None))
            .order_by("dist").limit(top_k)
        )
        return [(reg, dist) for reg, dist in result.all()]

    async def _keyword_search(self, session: AsyncSession, pack: str, query_text: str, top_k: int) -> list[Regulation]:
        terms = _keywords(query_text)
        if not terms:
            return []
        conditions = [Regulation.content.ilike(f"%{t}%") for t in terms]
        result = await session.execute(
            select(Regulation).where(Regulation.pack == pack, or_(*conditions)).limit(top_k)
        )
        return list(result.scalars().all())
