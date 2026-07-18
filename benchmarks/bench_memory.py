"""Benchmark: Persistent storage comparison.

Compares the storage footprint of three approaches for the same knowledge:
  1. DSR KnowledgeAtoms (minimal invariants only)
  2. Graph DB triples (explicit relationships + properties)
  3. Vector DB records (embeddings + metadata)

Answers Research Question 1:
  "Can persistent memory be significantly reduced compared to graphs
   and vector databases?"

Run:  python benchmarks/bench_memory.py
"""

from __future__ import annotations

import json
import sys

import numpy as np

from dsr import KnowledgeAtom, Constraint, Operator


def build_atoms(n: int) -> list[KnowledgeAtom]:
    """Generate n atoms simulating a vehicle telemetry domain."""
    atoms = []
    for i in range(n):
        atoms.append(KnowledgeAtom(
            atom_id=f"sensor_{i:04d}",
            sigma={
                "type": "temperature_sensor",
                "unit": "celsius",
                "range_min": -40,
                "range_max": 150,
                "precision": 0.1,
                "location": f"zone_{i % 8}",
            },
            constraints=[
                Constraint("range_check", lambda b, lo=-40, hi=150: lo <= b.get("value", 0) <= hi),
            ],
            operators=[
                Operator("normalize", lambda s, c: {
                    "_head": "normalized",
                    "value": (c.get("value", 25) - s["range_min"]) / (s["range_max"] - s["range_min"]),
                }),
                Operator("alert_check", lambda s, c: {
                    "_head": "alert",
                    "triggered": c.get("value", 25) > s["range_max"] * 0.9,
                }),
            ],
            provenance="fleet_sensor_registry",
            confidence=0.95,
        ))
    return atoms


def simulate_graph_triples(n: int, avg_relations: int = 5) -> int:
    """Simulate storage for a property graph with n nodes and relationships."""
    triples = []
    for i in range(n):
        # node properties (stored as key-value pairs)
        node = {
            "id": f"sensor_{i:04d}",
            "type": "temperature_sensor",
            "unit": "celsius",
            "range_min": -40,
            "range_max": 150,
            "precision": 0.1,
            "location": f"zone_{i % 8}",
            "provenance": "fleet_sensor_registry",
            "confidence": 0.95,
        }
        triples.append(json.dumps(node))

        # explicit relationships
        for r in range(avg_relations):
            target = (i + r + 1) % n
            rel = {
                "source": f"sensor_{i:04d}",
                "target": f"sensor_{target:04d}",
                "type": "co_located" if r < 2 else "correlated",
                "weight": 0.8,
                "metadata": {"computed_at": "2026-01-01"},
            }
            triples.append(json.dumps(rel))

    return sum(len(t.encode()) for t in triples)


def simulate_vector_db(n: int, dims: int = 384) -> int:
    """Simulate storage for a vector database with n records."""
    total = 0
    for i in range(n):
        # embedding (float32)
        embedding_bytes = dims * 4  # 4 bytes per float32

        # metadata
        meta = json.dumps({
            "id": f"sensor_{i:04d}",
            "type": "temperature_sensor",
            "unit": "celsius",
            "range_min": -40,
            "range_max": 150,
            "precision": 0.1,
            "location": f"zone_{i % 8}",
            "provenance": "fleet_sensor_registry",
            "confidence": 0.95,
        })
        total += embedding_bytes + len(meta.encode())

    return total


def main():
    print("=" * 70)
    print("Benchmark: Persistent Storage Comparison")
    print("=" * 70)
    print()

    sizes = [10, 50, 100, 500, 1000, 5000]

    print(f"{'N atoms':>10} | {'DSR (bytes)':>14} | {'Graph DB':>14} | {'Vector DB':>14} | {'DSR/Graph':>10} | {'DSR/Vector':>10}")
    print("-" * 85)

    for n in sizes:
        atoms = build_atoms(n)
        dsr_bytes = sum(a.persistent_size_bytes() for a in atoms)
        graph_bytes = simulate_graph_triples(n, avg_relations=5)
        vector_bytes = simulate_vector_db(n, dims=384)

        ratio_graph = dsr_bytes / graph_bytes if graph_bytes > 0 else 0
        ratio_vector = dsr_bytes / vector_bytes if vector_bytes > 0 else 0

        print(
            f"{n:>10} | {dsr_bytes:>14,} | {graph_bytes:>14,} | {vector_bytes:>14,} | "
            f"{ratio_graph:>9.1%} | {ratio_vector:>9.1%}"
        )

    print()
    print("DSR/Graph  = ratio of DSR storage to graph storage (lower = better)")
    print("DSR/Vector = ratio of DSR storage to vector DB storage (lower = better)")
    print()
    print("Key finding: DSR stores only invariants — no edges, no embeddings.")
    print("Edges and embeddings are generated on demand when needed.")
    print()

    # Breakdown for a single atom
    print("-" * 70)
    print("Single atom breakdown")
    print("-" * 70)
    atom = build_atoms(1)[0]
    serialized = atom.to_minimal_dict()
    raw = json.dumps(serialized, indent=2)
    print(f"  Persistent form ({len(raw.encode())} bytes):")
    print()
    for line in raw.split("\n"):
        print(f"    {line}")
    print()
    print(f"  Equivalent graph node + 5 edges: ~{simulate_graph_triples(1, 5)} bytes")
    print(f"  Equivalent vector record (384d):  ~{simulate_vector_db(1, 384)} bytes")
    print(f"  Reduction factor (vs graph):      {simulate_graph_triples(1, 5) / len(raw.encode()):.1f}x")
    print(f"  Reduction factor (vs vector):     {simulate_vector_db(1, 384) / len(raw.encode()):.1f}x")


if __name__ == "__main__":
    main()
