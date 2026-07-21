"""Incident Pattern Intelligence — cross-references the current risk situation against
past incidents and near-misses using the same real vector search as the Compliance
Agent (embeddings/local.py), instead of an LLM guessing "this seems familiar" from
memory. Surfaces the closest matches as a concrete "this has happened before" signal,
which is what turns a one-off alert into an actionable prevention priority.

The closest match's cosine distance also becomes a bounded numeric score (see
`_similarity_score`), fed into the compound risk calculation the same way the
Compliance Agent's regulation matches already are (agents/coordinator.py) — a past
INCIDENT counts more than a NEAR_MISS, since a near-miss was caught before harm.
Only vector search produces a comparable confidence measure; the keyword fallback
has no ranking, so it never contributes a score, only the "similar past X" text.
"""
from __future__ import annotations
import asyncio
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Incident, NearMiss
from embeddings.base import Embedder

_STOPWORDS = {"the", "a", "an", "in", "of", "to", "and", "or", "for", "is", "on", "at", "safety", "conditions", "readings"}

# Cosine distance beyond which a "closest match" isn't actually similar enough to mean
# anything — calibrated against real matches observed in this project's own live
# testing (genuine matches landed ~0.30-0.38); past that, don't manufacture a signal.
SIMILARITY_CUTOFF = 0.5
NEAR_MISS_WEIGHT = 0.5  # a near-miss was caught before harm — half the weight of a real incident


def _similarity_score(closest: dict) -> float:
    distance = closest.get("distance")
    if distance is None or distance >= SIMILARITY_CUTOFF:
        return 0.0
    similarity = 1.0 - (distance / SIMILARITY_CUTOFF)
    weight = 1.0 if closest["type"] == "incident" else NEAR_MISS_WEIGHT
    return round(similarity * weight, 3)


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


class IncidentAgent:
    def __init__(self, embedder: Embedder | None = None):
        self.embedder = embedder

    async def assess(self, session: AsyncSession, query_text: str, top_k: int = 3) -> dict:
        if not query_text:
            return {"agent": "incident", "matches": [], "score": 0.0, "retrieval": "none"}

        matches: list[dict] | None = None
        retrieval = "vector"
        if self.embedder:
            try:
                matches = await self._vector_search(session, query_text, top_k)
            except Exception:
                matches = None

        if matches is None:
            retrieval = "keyword"
            matches = await self._keyword_search(session, query_text, top_k)

        # Only vector search gives a distance to score against — keyword hits have no
        # ranking, so they inform the text but never move the number.
        score = _similarity_score(matches[0]) if matches and retrieval == "vector" else 0.0

        return {"agent": "incident", "matches": matches, "score": score, "retrieval": retrieval}

    async def _vector_search(self, session: AsyncSession, query_text: str, top_k: int) -> list[dict]:
        query_vec = await asyncio.to_thread(self.embedder.embed_query, query_text)

        incident_result = await session.execute(
            select(Incident, Incident.embedding.cosine_distance(query_vec).label("dist"))
            .where(Incident.embedding.is_not(None))
            .order_by("dist").limit(top_k)
        )
        near_miss_result = await session.execute(
            select(NearMiss, NearMiss.embedding.cosine_distance(query_vec).label("dist"))
            .where(NearMiss.embedding.is_not(None))
            .order_by("dist").limit(top_k)
        )

        combined = [
            {
                "type": "incident", "id": i.id, "zone_id": i.zone_id, "date": i.incident_date.isoformat() if i.incident_date else None,
                "description": i.description, "severity": i.severity, "root_cause": i.root_cause, "distance": dist,
            }
            for i, dist in incident_result.all()
        ] + [
            {
                "type": "near_miss", "id": n.id, "zone_id": n.zone_id, "date": n.report_date.isoformat() if n.report_date else None,
                "description": n.description, "reported_by": n.reported_by, "distance": dist,
            }
            for n, dist in near_miss_result.all()
        ]
        combined.sort(key=lambda m: m["distance"])
        return combined[:top_k]

    async def _keyword_search(self, session: AsyncSession, query_text: str, top_k: int) -> list[dict]:
        terms = _keywords(query_text)
        if not terms:
            return []
        from sqlalchemy import or_
        conditions_i = [Incident.description.ilike(f"%{t}%") for t in terms]
        conditions_n = [NearMiss.description.ilike(f"%{t}%") for t in terms]

        incidents = (await session.execute(select(Incident).where(or_(*conditions_i)).limit(top_k))).scalars().all()
        near_misses = (await session.execute(select(NearMiss).where(or_(*conditions_n)).limit(top_k))).scalars().all()

        combined = [
            {"type": "incident", "id": i.id, "zone_id": i.zone_id, "date": i.incident_date.isoformat() if i.incident_date else None,
             "description": i.description, "severity": i.severity, "root_cause": i.root_cause}
            for i in incidents
        ] + [
            {"type": "near_miss", "id": n.id, "zone_id": n.zone_id, "date": n.report_date.isoformat() if n.report_date else None,
             "description": n.description, "reported_by": n.reported_by}
            for n in near_misses
        ]
        return combined[:top_k]
