# Dynamic Semantic Runtime (DSR)

**A knowledge representation architecture based on on-demand generation instead of explicit relationship persistence.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Research Hypothesis

Current AI architectures represent knowledge through persistent structures (Knowledge Graphs, Property Graphs), fixed embeddings, and static metadata. This approach:

- Persists vast quantities of relationships that are never queried.
- Stores embeddings as fixed state, although their meaning depends on context.
- Maintains metadata driven by storage needs rather than reasoning needs.
- Enforces a rigid separation between storage, representation, and inference.

**DSR proposes the opposite**: persist only a minimal set of invariants plus a dynamic generation mechanism for representations.

```
Knowledge != Stored Graph
Knowledge  = Invariant Representation + Transformation Functions + Context
```

## Core Concept: The Knowledge Atom

The fundamental persistent unit is not a graph node. It is a **Knowledge Atom**:

```python
KnowledgeAtom = <Id, Sigma, Constraints, Operators, Provenance, Confidence, Version>
```

| Component | Role |
|---|---|
| `Id` | Stable unique identifier |
| `Sigma` | Minimal isomorphic signature (algebraic type constants) |
| `Constraints` | First-order logic predicates defining invariance boundaries |
| `Operators` | Pure endomorphism functions (self-transformations) |
| `Provenance` | Origin chain |
| `Confidence` | Certainty measure |
| `Version` | Monotonic version counter |

**What it does NOT store**: embeddings, neighbor lists, materialized hierarchies, explicit relationships.

## Architecture

```
KnowledgeAtom
      |
      v
Query + Context
      |
      v
Representation Generator (E-Graph Unification)
      |
      v
Temporary Representation (ephemeral embedding or subgraph)
      |
      v
Inference
      |
      v
Discard or Adaptive Cache
```

### Paradigm Shift

| Traditional | DSR |
|---|---|
| Persistence -> Representation -> Inference | Minimal Persistence -> Dynamic Generation -> Temporal Representation -> Inference -> Adaptive Materialization |
| Persistent relationships | Generated relationships |
| Fixed embeddings | Ephemeral embeddings |
| Expensive updates | Minimal persistence |
| Explicit topology | Contextual topology |

### Relationship Generation via E-Graphs

Relationships are not stored. They emerge through **semantic unification**:

```
[Atom A: Water] --(Phase Transition Operator)--> [Intermediate Term]
                                                        | (E-Graph Unification)
[Atom B: Steam] -----------------------------------------------+
```

Two atoms are related when their transformation operators produce terms that unify in the same equivalence class. This is computable in milliseconds on a standard CPU using term-rewriting algorithms.

## Mathematical Model

Let `K` be the set of Knowledge Atoms. A representation is:

```
R = G(K, Q, C)
```

Where `G` is the Representation Generator, `Q` is the Query, and `C` is the Context.

The objective function minimizes:

```
J = InferenceCost + StorageCost + UpdateCost + SynchronizationCost
```

Without necessarily maximizing knowledge persistence.

## Research Questions

1. Can persistent memory be significantly reduced compared to graphs and vector databases?
2. What is the cost of generating representations on-demand versus persisting them?
3. Can an adaptive policy automatically decide what to materialize?
4. Do minimal invariants sufficient to reconstruct arbitrary knowledge exist?
5. Can this model integrate as a semantic runtime on conventional hardware?
6. Can semantic representation be fully decoupled from physical storage representation?

## Quick Start

```bash
# Clone
git clone https://github.com/DavidCaastro/dynamic-semantic-runtime.git
cd dynamic-semantic-runtime

# Install (no external dependencies beyond numpy)
pip install -e .

# Run examples
python examples/vehicle_telemetry.py
python examples/business_rules.py

# Run benchmarks
python benchmarks/bench_memory.py
python benchmarks/bench_latency.py

# Run tests
python -m pytest tests/ -v
```

### Requirements

- Python 3.10+
- numpy (only dependency)
- No Docker, no cloud, no GPU required

## Project Structure

```
src/dsr/
  atom.py        # KnowledgeAtom definition and algebraic structure
  context.py     # Query and Context specification
  generator.py   # Representation Generator (ephemeral embeddings)
  egraph.py      # E-Graph: term rewriting and semantic unification
  cache.py       # Adaptive caching policy
  runtime.py     # DSR runtime orchestrator

benchmarks/
  bench_memory.py   # Storage: DSR atoms vs graph triples vs vector DB
  bench_latency.py  # Latency: on-demand generation vs pre-stored retrieval

examples/
  vehicle_telemetry.py  # Domain: fleet sensor data
  business_rules.py     # Domain: API business logic transitions
```

## Computational Analogy

This proposal is analogous to the paradigm shift introduced by compilers:

- **Before**: store results.
- **After**: store rules capable of producing results.

DSR proposes: **do not store materialized knowledge. Store the minimal rules capable of reconstructing any necessary representation.**

## Positioning

DSR does not aim to replace Knowledge Graphs, Vector Databases, Embeddings, or Neuro-Symbolic AI individually. It introduces a **higher abstraction level** where these mechanisms cease to be persistent and become dynamically materialized representations from a minimal knowledge unit and a contextual generator.

## Open Problem

The core scientific challenge is not designing the runtime but **discovering what the minimal unit is upon which the runtime can operate**. If the KnowledgeAtom cannot be defined in a consistent and compositional way, the rest of the architecture loses its foundation.

## License

MIT License. See [LICENSE](LICENSE).

## Author

David Castro - [GitHub](https://github.com/DavidCaastro)
