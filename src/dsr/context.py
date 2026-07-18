"""Query and Context — the stimulus that triggers representation generation.

In DSR, knowledge is inert until a Query arrives within a Context.
The pair (Q, C) determines *which* atoms are relevant and *how* their
operators should be evaluated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Query:
    """A request for knowledge.

    Attributes:
        intent:     what kind of answer is expected (e.g. "relate", "describe", "infer")
        targets:    atom IDs or sigma patterns to match
        parameters: additional key-value pairs that constrain the search
    """

    intent: str
    targets: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)

    def matches_atom_id(self, atom_id: str) -> bool:
        if not self.targets:
            return True
        return atom_id in self.targets


@dataclass(frozen=True, slots=True)
class Context:
    """Environmental conditions under which representation is generated.

    The same atom can produce different representations under different
    contexts — this is the key insight that makes ephemeral embeddings
    superior to fixed ones.

    Attributes:
        domain:      semantic domain (e.g. "thermodynamics", "finance")
        dimensions:  desired dimensionality of generated embeddings
        constraints: additional runtime constraints (e.g. max latency)
        bindings:    variable bindings for constraint evaluation
    """

    domain: str = "general"
    dimensions: int = 64
    constraints: dict[str, Any] = field(default_factory=dict)
    bindings: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "dimensions": self.dimensions,
            **self.constraints,
            **self.bindings,
        }
