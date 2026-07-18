"""NetworkX benchmark runner."""

from __future__ import annotations

import json
import sys
import time

import networkx as nx

from dashboard.utils import compute_stats


def _build_graph(n: int, relations_per_node: int) -> nx.DiGraph:
    """Build a directed graph with n nodes and explicit relationships."""
    G = nx.DiGraph()
    for i in range(n):
        G.add_node(f"node_{i:04d}", **{
            "type": "sensor",
            "value_range": [0, 100],
            "unit": "celsius",
            "zone": f"z{i % 10}",
            "provenance": "sensor_registry",
            "confidence": 0.95,
        })
    for i in range(n):
        for r in range(relations_per_node):
            target = (i + r + 1) % n
            G.add_edge(
                f"node_{i:04d}",
                f"node_{target:04d}",
                type="co_located" if r < 2 else "correlated",
                weight=0.8,
            )
    return G


def _estimate_graph_memory(G: nx.DiGraph) -> int:
    """Estimate memory usage of a NetworkX graph via JSON serialization."""
    data = nx.node_link_data(G)
    return len(json.dumps(data).encode())


def run(n: int, relations_per_node: int = 5, rounds: int = 50, **_kwargs) -> dict:
    """Run NetworkX benchmark and return stats."""
    # Build graph
    G = _build_graph(n, relations_per_node)

    # Benchmark: neighbor lookup + shortest path as query proxy
    times = []
    nodes = list(G.nodes())
    for r in range(rounds):
        t0 = time.perf_counter()
        for node in nodes:
            list(G.neighbors(node))
        # shortest path on a sample pair
        if len(nodes) >= 2:
            try:
                nx.shortest_path(G, nodes[0], nodes[min(n - 1, len(nodes) - 1)])
            except nx.NetworkXNoPath:
                pass
        elapsed = (time.perf_counter() - t0) * 1_000_000
        times.append(elapsed)

    memory_bytes = _estimate_graph_memory(G)

    stats = compute_stats(times)
    stats["memory_bytes"] = memory_bytes
    stats["per_atom_us"] = stats["mean"] / n if n > 0 else 0
    stats["per_atom_bytes"] = memory_bytes / n if n > 0 else 0

    return stats
