"""KnowledgeAtom — the minimal persistent unit of knowledge in DSR.

A KnowledgeAtom is NOT a database record.  It is an algebraic specification:
the *source code* of knowledge.  Embeddings and relationships are the
*compiled binaries* — generated on demand, consumed, then discarded.

Formal structure:  A = <Id, Sigma, C, O>
  - Id:    stable unique identifier
  - Sigma: minimal isomorphic signature (type constants)
  - C:     constraint sheaf (first-order predicates)
  - O:     endomorphism operators (pure rewrite functions)
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Constraint — a first-order predicate that defines invariance boundaries
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Constraint:
    """A named predicate that must hold for the atom to be valid.

    The predicate receives a dict of bindings and returns True/False.
    Example: Constraint("pv=nrt", lambda b: abs(b["P"]*b["V"] - b["n"]*b["R"]*b["T"]) < 1e-6)
    """

    name: str
    predicate: Callable[[dict[str, Any]], bool]

    def check(self, bindings: dict[str, Any]) -> bool:
        return self.predicate(bindings)

    def __repr__(self) -> str:
        return f"Constraint({self.name!r})"


# ---------------------------------------------------------------------------
# Operator — a pure endomorphism (self-transformation)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Operator:
    """A named pure function that transforms the atom's signature space.

    Operators produce *terms* that can unify with other atoms in an E-Graph,
    enabling relationship discovery without persistent edges.

    The function receives (sigma, context_dict) and returns a new term (dict).
    """

    name: str
    transform: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]

    def apply(self, sigma: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.transform(sigma, context or {})

    def __repr__(self) -> str:
        return f"Operator({self.name!r})"


# ---------------------------------------------------------------------------
# KnowledgeAtom
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class KnowledgeAtom:
    """The minimal persistent unit of knowledge.

    Persistent fields (survive at rest):
        atom_id, sigma, constraints, operators, provenance, confidence, version

    NOT persisted:
        embeddings, neighbor lists, materialized hierarchies, explicit edges.
    """

    atom_id: str
    sigma: dict[str, Any]
    constraints: list[Constraint] = field(default_factory=list)
    operators: list[Operator] = field(default_factory=list)
    provenance: str = ""
    confidence: float = 1.0
    version: int = 1

    # -- internal bookkeeping (not serialized) --
    _created_at: float = field(default_factory=time.time, repr=False)

    # ---- identity ----

    @property
    def fingerprint(self) -> str:
        """Content-addressable hash of the atom's invariant core."""
        raw = f"{self.atom_id}:{sorted(self.sigma.items())}:{self.version}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    # ---- constraint validation ----

    def validate(self, bindings: dict[str, Any]) -> bool:
        """Check all constraints against the given bindings."""
        return all(c.check(bindings) for c in self.constraints)

    # ---- operator application ----

    def apply_operator(self, name: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Apply a named operator and return the resulting term."""
        for op in self.operators:
            if op.name == name:
                return op.apply(self.sigma, context)
        raise KeyError(f"Operator {name!r} not found in atom {self.atom_id!r}")

    def all_terms(self, context: dict[str, Any] | None = None) -> list[tuple[str, dict[str, Any]]]:
        """Apply every operator and return [(op_name, resulting_term), ...]."""
        return [(op.name, op.apply(self.sigma, context)) for op in self.operators]

    # ---- serialization (persistent form) ----

    def to_minimal_dict(self) -> dict[str, Any]:
        """Serialize to the minimal persistent representation.

        Operators and constraints are stored by name only — their code lives
        in a registry, not in the serialized form.
        """
        return {
            "atom_id": self.atom_id,
            "sigma": self.sigma,
            "constraints": [c.name for c in self.constraints],
            "operators": [o.name for o in self.operators],
            "provenance": self.provenance,
            "confidence": self.confidence,
            "version": self.version,
        }

    # ---- size measurement ----

    def persistent_size_bytes(self) -> int:
        """Approximate serialized size in bytes (JSON-like)."""
        import json
        return len(json.dumps(self.to_minimal_dict()).encode())

    def __repr__(self) -> str:
        return (
            f"KnowledgeAtom(id={self.atom_id!r}, sigma_keys={list(self.sigma.keys())}, "
            f"constraints={len(self.constraints)}, operators={len(self.operators)}, "
            f"v={self.version}, conf={self.confidence:.2f})"
        )
