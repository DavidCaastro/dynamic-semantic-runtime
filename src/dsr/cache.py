"""Adaptive Cache — learns which representations are worth keeping.

DSR does not make a fixed decision between persisting and computing.
It maintains a dynamic policy:

    Frequently Used  ->  Materialize  ->  Cache  ->  Reuse
    Else             ->  Recompute

The cache tracks access frequency, recency, and generation cost to
decide eviction.  This is a CPU-friendly LFU/LRU hybrid.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from dsr.generator import EphemeralRepresentation


@dataclass
class CacheEntry:
    representation: EphemeralRepresentation
    access_count: int = 1
    last_access: float = field(default_factory=time.time)
    generation_cost_us: float = 0.0  # microseconds to generate

    @property
    def score(self) -> float:
        """Higher score = more worth keeping.

        Combines frequency, recency, and generation cost.
        """
        recency = 1.0 / (1.0 + (time.time() - self.last_access))
        return self.access_count * recency * (1.0 + self.generation_cost_us / 1000.0)


class AdaptiveCache:
    """Context-aware representation cache.

    Keys are (atom_id, context_hash) tuples — the same atom under
    different contexts produces different cache entries.
    """

    def __init__(self, max_entries: int = 1000) -> None:
        self.max_entries = max_entries
        self._store: dict[tuple[str, str], CacheEntry] = {}
        self._hits: int = 0
        self._misses: int = 0

    def get(self, atom_id: str, context_hash: str) -> EphemeralRepresentation | None:
        key = (atom_id, context_hash)
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        entry.access_count += 1
        entry.last_access = time.time()
        self._hits += 1
        return entry.representation

    def put(
        self,
        rep: EphemeralRepresentation,
        generation_cost_us: float = 0.0,
    ) -> None:
        key = (rep.atom_id, rep.context_hash)
        self._store[key] = CacheEntry(
            representation=rep,
            generation_cost_us=generation_cost_us,
        )
        if len(self._store) > self.max_entries:
            self._evict()

    def _evict(self) -> None:
        """Evict the entry with the lowest adaptive score."""
        if not self._store:
            return
        worst_key = min(self._store, key=lambda k: self._store[k].score)
        del self._store[worst_key]

    def clear(self) -> None:
        self._store.clear()

    def stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {
            "entries": len(self._store),
            "max_entries": self.max_entries,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
            "memory_bytes": sum(
                e.representation.size_bytes() for e in self._store.values()
            ),
        }
