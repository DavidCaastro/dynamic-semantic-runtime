"""DSR benchmark runner."""

from __future__ import annotations

import time

from dsr import DSRRuntime, Query, Context

from dashboard.utils import build_atoms, compute_stats


def run(n: int, dims: int, domain: str, rounds: int = 50) -> dict:
    """Run DSR benchmark and return stats."""
    atoms = build_atoms(n, domain)
    runtime = DSRRuntime(default_dims=dims)
    runtime.register_many(atoms)

    ctx = Context(domain=domain, dimensions=dims, bindings={"reading": 72})
    query = Query(intent="analyze")

    # Latency benchmark
    times = []
    for _ in range(rounds):
        runtime.clear_cache()
        t0 = time.perf_counter()
        runtime.query(query, ctx)
        elapsed = (time.perf_counter() - t0) * 1_000_000
        times.append(elapsed)

    # Memory
    memory_bytes = runtime.total_persistent_bytes()

    stats = compute_stats(times)
    stats["memory_bytes"] = memory_bytes
    stats["per_atom_us"] = stats["mean"] / n if n > 0 else 0
    stats["per_atom_bytes"] = memory_bytes / n if n > 0 else 0

    return stats


def run_cache_comparison(n: int, dims: int, domain: str, rounds: int = 50) -> dict:
    """Run cold vs warm cache comparison and return stats for both."""
    atoms = build_atoms(n, domain)
    runtime = DSRRuntime(default_dims=dims)
    runtime.register_many(atoms)

    ctx = Context(domain=domain, dimensions=dims, bindings={"reading": 72})
    query = Query(intent="analyze")

    # Cold: clear cache before each query
    cold_times = []
    for _ in range(rounds):
        runtime.clear_cache()
        t0 = time.perf_counter()
        runtime.query(query, ctx)
        cold_times.append((time.perf_counter() - t0) * 1_000_000)

    # Warm: cache already populated from last cold run
    warm_times = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        runtime.query(query, ctx)
        warm_times.append((time.perf_counter() - t0) * 1_000_000)

    cold_stats = compute_stats(cold_times)
    warm_stats = compute_stats(warm_times)

    return {"cold": cold_stats, "warm": warm_stats}
