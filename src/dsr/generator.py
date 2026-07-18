"""Representation Generator — produces ephemeral embeddings from atoms.

In traditional architectures, an embedding is a *property* of a data point,
computed once and stored forever.  In DSR, an embedding is a *function
evaluation* — contextual, temporary, and disposable.

    R = G(K, Q, C)

The generator reads the atom's sigma and operators, evaluates them under
the current context, and produces a dense vector that exists only as long
as inference needs it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from dsr.atom import KnowledgeAtom
from dsr.context import Context


@dataclass(slots=True)
class EphemeralRepresentation:
    """A temporary representation — the 'compiled binary' of knowledge."""

    atom_id: str
    vector: np.ndarray
    context_hash: str
    metadata: dict[str, Any]

    @property
    def dimensions(self) -> int:
        return len(self.vector)

    def cosine_similarity(self, other: EphemeralRepresentation) -> float:
        dot = float(np.dot(self.vector, other.vector))
        norm_a = float(np.linalg.norm(self.vector))
        norm_b = float(np.linalg.norm(other.vector))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def size_bytes(self) -> int:
        return self.vector.nbytes

    def __repr__(self) -> str:
        return (
            f"EphemeralRepresentation(atom={self.atom_id!r}, "
            f"dims={self.dimensions}, ctx={self.context_hash[:8]})"
        )


class RepresentationGenerator:
    """Generates ephemeral embeddings from KnowledgeAtoms.

    The generation strategy:
    1. Hash the atom's sigma keys + context to seed a deterministic PRNG.
    2. For each operator, apply it under the context to get a term dict.
    3. Encode term values into a dense vector via deterministic projection.
    4. Combine operator vectors with the sigma base vector.

    This is deterministic: same atom + same context = same embedding.
    Different context = different embedding — which is the whole point.
    """

    def __init__(self, default_dims: int = 64) -> None:
        self.default_dims = default_dims

    def generate(
        self,
        atom: KnowledgeAtom,
        context: Context | None = None,
    ) -> EphemeralRepresentation:
        ctx = context or Context(dimensions=self.default_dims)
        dims = ctx.dimensions
        ctx_dict = ctx.to_dict()

        # deterministic seed from atom identity + context
        seed_str = f"{atom.fingerprint}:{ctx.domain}:{sorted(ctx_dict.items())}"
        seed = int(hashlib.sha256(seed_str.encode()).hexdigest()[:8], 16)
        rng = np.random.RandomState(seed)

        # base vector from sigma, modulated by context
        base = self._encode_sigma(atom.sigma, dims, rng)
        # context modulation: domain shifts the base vector
        domain_hash = int(hashlib.md5(f"domain:{ctx.domain}".encode()).hexdigest()[:8], 16)
        domain_rng = np.random.RandomState(domain_hash)
        domain_shift = domain_rng.randn(dims) * 0.3
        base = base + domain_shift

        # operator contributions
        operator_vecs: list[np.ndarray] = []
        for op in atom.operators:
            try:
                term = op.apply(atom.sigma, ctx_dict)
                vec = self._encode_term(term, dims, rng)
                operator_vecs.append(vec)
            except Exception:
                pass

        # combine: base + mean of operator vectors (if any)
        if operator_vecs:
            op_mean = np.mean(operator_vecs, axis=0)
            combined = 0.6 * base + 0.4 * op_mean
        else:
            combined = base

        # L2 normalize
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined = combined / norm

        ctx_hash = hashlib.sha256(seed_str.encode()).hexdigest()[:16]

        return EphemeralRepresentation(
            atom_id=atom.atom_id,
            vector=combined.astype(np.float32),
            context_hash=ctx_hash,
            metadata={"domain": ctx.domain, "operators_applied": len(operator_vecs)},
        )

    def _encode_sigma(self, sigma: dict[str, Any], dims: int, rng: np.random.RandomState) -> np.ndarray:
        """Deterministically project sigma key-value pairs into a vector."""
        vec = np.zeros(dims, dtype=np.float64)
        for i, (key, value) in enumerate(sorted(sigma.items())):
            # hash key to get a position pattern
            key_hash = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
            key_rng = np.random.RandomState(key_hash)
            direction = key_rng.randn(dims)
            # scale by value magnitude if numeric
            scale = self._numeric_scale(value)
            vec += direction * scale
        return vec

    def _encode_term(self, term: dict[str, Any], dims: int, rng: np.random.RandomState) -> np.ndarray:
        """Encode an operator-produced term dict into a vector."""
        vec = np.zeros(dims, dtype=np.float64)
        for key, value in sorted(term.items()):
            if key.startswith("_"):
                continue
            key_hash = int(hashlib.md5(f"term:{key}".encode()).hexdigest()[:8], 16)
            key_rng = np.random.RandomState(key_hash)
            direction = key_rng.randn(dims)
            scale = self._numeric_scale(value)
            vec += direction * scale
        return vec

    @staticmethod
    def _numeric_scale(value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value) if abs(float(value)) > 1e-10 else 1.0
        if isinstance(value, str):
            return float(len(value)) / 10.0
        if isinstance(value, bool):
            return 1.0 if value else -1.0
        return 1.0
