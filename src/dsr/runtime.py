"""DSR Runtime — the orchestrator that ties everything together.

Lifecycle:
  1. REST:     atoms stored as compact JSON (bytes, not megabytes)
  2. STIMULUS: query + context arrive
  3. CRYSTAL:  generator produces ephemeral embeddings in RAM
  4. UNIFY:    E-Graph discovers emergent relationships
  5. CONSUME:  inference module uses the representations
  6. DISSOLVE: cache policy decides keep or discard
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from dsr.atom import KnowledgeAtom
from dsr.cache import AdaptiveCache
from dsr.context import Context, Query
from dsr.egraph import EGraph, Term
from dsr.generator import EphemeralRepresentation, RepresentationGenerator


@dataclass
class QueryResult:
    """The output of a DSR query."""

    representations: list[EphemeralRepresentation]
    relations: list[tuple[str, str, int]]
    egraph_stats: dict[str, int]
    cache_stats: dict[str, Any]
    generation_time_us: float
    atoms_evaluated: int


class DSRRuntime:
    """The Dynamic Semantic Runtime engine.

    Usage:
        runtime = DSRRuntime()
        runtime.register(atom1)
        runtime.register(atom2)
        result = runtime.query(query, context)
    """

    def __init__(
        self,
        default_dims: int = 64,
        cache_max: int = 1000,
    ) -> None:
        self._atoms: dict[str, KnowledgeAtom] = {}
        self._generator = RepresentationGenerator(default_dims=default_dims)
        self._cache = AdaptiveCache(max_entries=cache_max)
        self._egraph = EGraph()

    # ---- atom management ----

    def register(self, atom: KnowledgeAtom) -> None:
        self._atoms[atom.atom_id] = atom

    def register_many(self, atoms: list[KnowledgeAtom]) -> None:
        for a in atoms:
            self.register(a)

    def get_atom(self, atom_id: str) -> KnowledgeAtom | None:
        return self._atoms.get(atom_id)

    @property
    def atom_count(self) -> int:
        return len(self._atoms)

    # ---- query ----

    def query(self, query: Query, context: Context | None = None) -> QueryResult:
        """Execute a query against the runtime.

        1. Select relevant atoms
        2. Generate or retrieve cached representations
        3. Build E-Graph to discover relationships
        4. Return results + stats
        """
        ctx = context or Context()
        t0 = time.perf_counter()

        # select atoms matching the query
        relevant = [
            a for a in self._atoms.values()
            if query.matches_atom_id(a.atom_id)
        ]

        # generate representations (cache-aware)
        representations: list[EphemeralRepresentation] = []
        self._egraph.clear()

        for atom in relevant:
            # try cache first
            ctx_hash_preview = f"{atom.fingerprint}:{ctx.domain}"
            cached = self._cache.get(atom.atom_id, ctx_hash_preview[:16])
            if cached is not None:
                rep = cached
            else:
                gen_t0 = time.perf_counter()
                rep = self._generator.generate(atom, ctx)
                gen_cost = (time.perf_counter() - gen_t0) * 1_000_000
                self._cache.put(rep, generation_cost_us=gen_cost)

            representations.append(rep)

            # feed operator terms into E-Graph for unification
            for op_name, term_dict in atom.all_terms(ctx.to_dict()):
                term = Term.from_dict(term_dict)
                self._egraph.add(term, atom.atom_id)

        # discover emergent relationships
        relations = self._egraph.discover_relations()

        elapsed_us = (time.perf_counter() - t0) * 1_000_000

        return QueryResult(
            representations=representations,
            relations=relations,
            egraph_stats=self._egraph.stats(),
            cache_stats=self._cache.stats(),
            generation_time_us=elapsed_us,
            atoms_evaluated=len(relevant),
        )

    # ---- introspection ----

    def total_persistent_bytes(self) -> int:
        """Total storage if all atoms were serialized to JSON."""
        return sum(a.persistent_size_bytes() for a in self._atoms.values())

    def stats(self) -> dict[str, Any]:
        return {
            "atoms": self.atom_count,
            "persistent_bytes": self.total_persistent_bytes(),
            "cache": self._cache.stats(),
            "egraph": self._egraph.stats(),
        }

    def clear_cache(self) -> None:
        self._cache.clear()

    def clear_all(self) -> None:
        self._atoms.clear()
        self._cache.clear()
        self._egraph.clear()
