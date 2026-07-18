"""Benchmark: On-demand generation latency.

Measures the cost of generating representations dynamically versus
the implicit cost of maintaining pre-stored representations.

Answers Research Question 2:
  "What is the cost of generating representations on-demand
   versus persisting them?"

Run:  python benchmarks/bench_latency.py
"""

from __future__ import annotations

import time
import statistics

import numpy as np

from dsr import (
    KnowledgeAtom,
    Constraint,
    Operator,
    Query,
    Context,
    DSRRuntime,
    RepresentationGenerator,
)


def build_atoms(n: int) -> list[KnowledgeAtom]:
    atoms = []
    for i in range(n):
        atoms.append(KnowledgeAtom(
            atom_id=f"node_{i:04d}",
            sigma={
                "type": "sensor",
                "value_range": [0, 100],
                "unit": "celsius",
                "zone": f"z{i % 10}",
            },
            operators=[
                Operator("normalize", lambda s, c: {
                    "_head": "normalized",
                    "value": (c.get("reading", 50) - s["value_range"][0])
                    / (s["value_range"][1] - s["value_range"][0]),
                }),
                Operator("classify", lambda s, c: {
                    "_head": "class",
                    "label": "high" if c.get("reading", 50) > 75 else "normal",
                }),
            ],
        ))
    return atoms


def bench_single_generation(generator: RepresentationGenerator, atom: KnowledgeAtom, ctx: Context, rounds: int = 1000):
    """Measure single-atom generation latency."""
    times = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        generator.generate(atom, ctx)
        elapsed = (time.perf_counter() - t0) * 1_000_000  # microseconds
        times.append(elapsed)
    return times


def bench_runtime_query(runtime: DSRRuntime, n_atoms: int, rounds: int = 100):
    """Measure full runtime query latency (all atoms)."""
    ctx = Context(domain="telemetry", dimensions=64, bindings={"reading": 72})
    query = Query(intent="analyze")
    times = []
    for _ in range(rounds):
        runtime.clear_cache()
        t0 = time.perf_counter()
        runtime.query(query, ctx)
        elapsed = (time.perf_counter() - t0) * 1_000_000
        times.append(elapsed)
    return times


def bench_cache_benefit(runtime: DSRRuntime, rounds: int = 100):
    """Compare cold (no cache) vs warm (cached) query times."""
    ctx = Context(domain="telemetry", dimensions=64, bindings={"reading": 72})
    query = Query(intent="analyze")

    # cold
    cold_times = []
    for _ in range(rounds):
        runtime.clear_cache()
        t0 = time.perf_counter()
        runtime.query(query, ctx)
        cold_times.append((time.perf_counter() - t0) * 1_000_000)

    # warm (cache already populated from last cold run)
    warm_times = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        runtime.query(query, ctx)
        warm_times.append((time.perf_counter() - t0) * 1_000_000)

    return cold_times, warm_times


def print_stats(label: str, times: list[float]):
    print(f"  {label}:")
    print(f"    mean   = {statistics.mean(times):>10.1f} us")
    print(f"    median = {statistics.median(times):>10.1f} us")
    print(f"    p95    = {sorted(times)[int(len(times) * 0.95)]:>10.1f} us")
    print(f"    min    = {min(times):>10.1f} us")
    print(f"    max    = {max(times):>10.1f} us")


def main():
    print("=" * 70)
    print("Benchmark: On-Demand Generation Latency")
    print("=" * 70)

    generator = RepresentationGenerator(default_dims=64)
    ctx = Context(domain="telemetry", dimensions=64, bindings={"reading": 72})

    # --- Single atom generation ---
    print()
    print("-" * 70)
    print("1. Single atom generation (1000 rounds)")
    print("-" * 70)

    atom = build_atoms(1)[0]
    times = bench_single_generation(generator, atom, ctx, rounds=1000)
    print_stats("Single atom -> ephemeral embedding", times)

    # --- Scaling: generation time vs atom count ---
    print()
    print("-" * 70)
    print("2. Full query latency vs atom count (100 rounds each)")
    print("-" * 70)

    scale_sizes = [10, 50, 100, 500, 1000]
    print(f"\n  {'N atoms':>10} | {'Mean (us)':>12} | {'Median (us)':>12} | {'P95 (us)':>12} | {'Per-atom (us)':>14}")
    print("  " + "-" * 70)

    for n in scale_sizes:
        runtime = DSRRuntime(default_dims=64)
        runtime.register_many(build_atoms(n))
        times = bench_runtime_query(runtime, n, rounds=100)
        mean = statistics.mean(times)
        print(
            f"  {n:>10} | {mean:>12.1f} | {statistics.median(times):>12.1f} | "
            f"{sorted(times)[95]:>12.1f} | {mean / n:>14.2f}"
        )

    # --- Cache benefit ---
    print()
    print("-" * 70)
    print("3. Cache benefit: cold vs warm queries (100 atoms, 100 rounds)")
    print("-" * 70)

    runtime = DSRRuntime(default_dims=64)
    runtime.register_many(build_atoms(100))
    cold, warm = bench_cache_benefit(runtime, rounds=100)

    print_stats("Cold (generate all)", cold)
    print()
    print_stats("Warm (cache hit)", warm)

    cold_mean = statistics.mean(cold)
    warm_mean = statistics.mean(warm)
    speedup = cold_mean / warm_mean if warm_mean > 0 else float("inf")
    print(f"\n  Cache speedup: {speedup:.1f}x")

    # --- Comparison with simulated retrieval ---
    print()
    print("-" * 70)
    print("4. DSR generation vs simulated persistent retrieval")
    print("-" * 70)

    n_compare = 100
    dims = 384

    # simulate vector DB retrieval (deserialize + copy)
    stored_vectors = [np.random.randn(dims).astype(np.float32) for _ in range(n_compare)]
    retrieval_times = []
    for _ in range(1000):
        t0 = time.perf_counter()
        # simulate: read from memory, copy, normalize
        results = []
        for vec in stored_vectors:
            v = vec.copy()
            v /= np.linalg.norm(v)
            results.append(v)
        retrieval_times.append((time.perf_counter() - t0) * 1_000_000)

    # DSR generation
    runtime2 = DSRRuntime(default_dims=dims)
    runtime2.register_many(build_atoms(n_compare))
    dsr_times = bench_runtime_query(runtime2, n_compare, rounds=100)

    print_stats(f"Simulated retrieval ({n_compare} x {dims}d)", retrieval_times)
    print()
    print_stats(f"DSR generation ({n_compare} atoms, {dims}d)", dsr_times)

    ret_mean = statistics.mean(retrieval_times)
    dsr_mean = statistics.mean(dsr_times)
    ratio = dsr_mean / ret_mean if ret_mean > 0 else float("inf")
    print(f"\n  DSR/Retrieval ratio: {ratio:.1f}x")
    print(f"  (Ratio > 1 means DSR is slower, but eliminates all persistent storage)")

    print()
    print("=" * 70)
    print("Conclusion: DSR trades ~Nx compute for ~0 persistent storage.")
    print("The adaptive cache closes the gap for frequently-accessed atoms.")
    print("=" * 70)


if __name__ == "__main__":
    main()
