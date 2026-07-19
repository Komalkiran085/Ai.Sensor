"""Embedder interface — one abstraction for turning text into a vector, so the
Compliance Agent's retrieval step doesn't care whether that vector came from a local
model or a cloud API. Same pluggability pattern as connectors/base.py.

Queries and passages are embedded separately on purpose: many retrieval-tuned models
(including the default local one) are asymmetric — a short query like "confined space
entry" and a long regulation clause aren't embedded the same way, even though they're
compared against each other.
"""
from __future__ import annotations
from abc import ABC, abstractmethod


class Embedder(ABC):
    dimension: int

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...

    @abstractmethod
    def embed_passage(self, text: str) -> list[float]: ...
