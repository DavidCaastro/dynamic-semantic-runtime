"""FAISS vector DB benchmark runner."""

from __future__ import annotations

import json
import time

import numpy as np

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

from dashboard.utils import compute_stats


def run(n: int, dims: int = 64, rounds: int = 50, **_kwargs) -> dict:
    """Run FAISS benchmark and return stats."""
    if not HAS_FAISS:
        return _run_fallback(n, dims, rounds)

    # Build index
    vectors = np.random.RandomState(42).randn(n, dims).astype(np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    vectors /= norms

    index = faiss.IndexFlatL2(dims)
    index.add(vectors)

    # Benchmark: search for k nearest neighbors
    k = min(10, n)
    query_vec = np.random.RandomState(99).randn(1, dims).astype(np.float32)

    times = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        index.search(query_vec, k)
        elapsed = (time.perf_counter() - t0) * 1_000_000
        times.append(elapsed)

    # Memory: embedding bytes + metadata
    embedding_bytes = n * dims * 4  # float32
    metadata_bytes = sum(
        len(json.dumps({
            "id": f"node_{i:04d}",
            "type": "sensor",
            "unit": "celsius",
            "zone": f"z{i % 10}",
        }).encode())
        for i in range(n)
    )
    memory_bytes = embedding_bytes + metadata_bytes

    stats = compute_stats(times)
    stats["memory_bytes"] = memory_bytes
    stats["per_atom_us"] = stats["mean"] / n if n > 0 else 0
    stats["per_atom_bytes"] = memory_bytes / n if n > 0 else 0

    return stats


def _run_fallback(n: int, dims: int, rounds: int) -> dict:
    """Fallback using pure numpy when FAISS is unavailable."""
    vectors = np.random.RandomState(42).randn(n, dims).astype(np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    vectors /= norms

    k = min(10, n)
    query_vec = np.random.RandomState(99).randn(1, dims).astype(np.float32)

    times = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        # brute force L2 search (same as IndexFlatL2)
        dists = np.sum((vectors - query_vec) ** 2, axis=1)
        top_k = np.argpartition(dists, k)[:k]
        _ = top_k[np.argsort(dists[top_k])]
        elapsed = (time.perf_counter() - t0) * 1_000_000
        times.append(elapsed)

    embedding_bytes = n * dims * 4
    metadata_bytes = sum(
        len(json.dumps({
            "id": f"node_{i:04d}",
            "type": "sensor",
            "unit": "celsius",
            "zone": f"z{i % 10}",
        }).encode())
        for i in range(n)
    )
    memory_bytes = embedding_bytes + metadata_bytes

    stats = compute_stats(times)
    stats["memory_bytes"] = memory_bytes
    stats["per_atom_us"] = stats["mean"] / n if n > 0 else 0
    stats["per_atom_bytes"] = memory_bytes / n if n > 0 else 0

    return stats
