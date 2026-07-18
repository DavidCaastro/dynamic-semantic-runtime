"""Helpers: atom builders, stats formatters."""

from __future__ import annotations

import statistics
from typing import Any

import pandas as pd

from dsr import KnowledgeAtom, Constraint, Operator


def build_atoms(n: int, domain: str = "telemetry") -> list[KnowledgeAtom]:
    """Generate n atoms for benchmarking."""
    atoms = []
    for i in range(n):
        if domain == "telemetry":
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
                constraints=[
                    Constraint("range_check", lambda b, lo=0, hi=100: lo <= b.get("value", 0) <= hi),
                ],
                provenance="sensor_registry",
                confidence=0.95,
            ))
        else:  # business_rules
            atoms.append(KnowledgeAtom(
                atom_id=f"rule_{i:04d}",
                sigma={
                    "type": "business_rule",
                    "category": f"cat_{i % 5}",
                    "priority": i % 3,
                    "scope": f"dept_{i % 4}",
                },
                operators=[
                    Operator("evaluate", lambda s, c: {
                        "_head": "evaluation",
                        "priority": s["priority"],
                        "applies": c.get("dept", "any") == s["scope"] or s["scope"] == "dept_0",
                    }),
                    Operator("audit", lambda s, c: {
                        "_head": "audit_entry",
                        "rule_type": s["type"],
                        "category": s["category"],
                    }),
                ],
                provenance="rule_engine",
                confidence=0.90,
            ))
    return atoms


def compute_stats(times: list[float]) -> dict[str, float]:
    """Compute latency statistics from a list of times in microseconds."""
    sorted_t = sorted(times)
    n = len(sorted_t)
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "p50": sorted_t[int(n * 0.50)],
        "p95": sorted_t[int(n * 0.95)] if n > 1 else sorted_t[-1],
        "p99": sorted_t[int(n * 0.99)] if n > 1 else sorted_t[-1],
        "min": min(times),
        "max": max(times),
    }


def stats_to_dataframe(results: dict[str, dict[str, float]]) -> pd.DataFrame:
    """Convert {approach: stats_dict} to a formatted DataFrame."""
    rows = []
    for approach, stats in results.items():
        rows.append({"Approach": approach, **stats})
    return pd.DataFrame(rows).set_index("Approach")
