"""Core test suite for DSR.

Validates the fundamental invariants of the Dynamic Semantic Runtime:
  - Atoms are immutable algebraic specifications
  - Representations are ephemeral and context-dependent
  - Relationships emerge from E-Graph unification, not storage
  - Cache adapts to access patterns
"""

import numpy as np
import pytest

from dsr import (
    KnowledgeAtom,
    Constraint,
    Operator,
    Query,
    Context,
    RepresentationGenerator,
    EGraph,
    Term,
    AdaptiveCache,
    DSRRuntime,
)


# ---- Fixtures ----

@pytest.fixture
def simple_atom():
    return KnowledgeAtom(
        atom_id="test_atom_1",
        sigma={"type": "sensor", "value": 42, "unit": "celsius"},
        constraints=[
            Constraint("positive", lambda b: b.get("value", 0) > 0),
        ],
        operators=[
            Operator("double", lambda s, c: {"_head": "scaled", "value": s["value"] * 2}),
            Operator("normalize", lambda s, c: {"_head": "normalized", "ratio": s["value"] / 100}),
        ],
    )


@pytest.fixture
def related_atoms():
    """Two atoms whose operators produce terms that should unify."""
    def energy_op(s, c):
        return {"_head": "energy", "type": "kinetic", "joules": s["mass"] * 10}

    a = KnowledgeAtom(
        atom_id="object_a",
        sigma={"mass": 50, "category": "vehicle"},
        operators=[Operator("energy", energy_op)],
    )
    b = KnowledgeAtom(
        atom_id="object_b",
        sigma={"mass": 50, "category": "projectile"},
        operators=[Operator("energy", energy_op)],
    )
    return a, b


# ---- KnowledgeAtom ----

class TestKnowledgeAtom:
    def test_fingerprint_deterministic(self, simple_atom):
        fp1 = simple_atom.fingerprint
        fp2 = simple_atom.fingerprint
        assert fp1 == fp2

    def test_fingerprint_changes_with_version(self, simple_atom):
        fp1 = simple_atom.fingerprint
        simple_atom.version = 2
        fp2 = simple_atom.fingerprint
        assert fp1 != fp2

    def test_constraint_validation_pass(self, simple_atom):
        assert simple_atom.validate({"value": 10})

    def test_constraint_validation_fail(self, simple_atom):
        assert not simple_atom.validate({"value": -5})

    def test_apply_operator(self, simple_atom):
        result = simple_atom.apply_operator("double")
        assert result == {"_head": "scaled", "value": 84}

    def test_apply_unknown_operator(self, simple_atom):
        with pytest.raises(KeyError):
            simple_atom.apply_operator("nonexistent")

    def test_all_terms(self, simple_atom):
        terms = simple_atom.all_terms()
        assert len(terms) == 2
        names = [t[0] for t in terms]
        assert "double" in names
        assert "normalize" in names

    def test_serialization_minimal(self, simple_atom):
        d = simple_atom.to_minimal_dict()
        assert "atom_id" in d
        assert d["constraints"] == ["positive"]
        assert d["operators"] == ["double", "normalize"]
        # no embeddings, no neighbors
        assert "embedding" not in d
        assert "neighbors" not in d

    def test_persistent_size(self, simple_atom):
        size = simple_atom.persistent_size_bytes()
        assert size > 0
        assert size < 1000  # should be very compact


# ---- E-Graph ----

class TestEGraph:
    def test_add_and_find(self):
        eg = EGraph()
        t = Term(head="energy", children={"type": "kinetic", "joules": 500})
        cid = eg.add(t, "atom_a")
        assert eg.find(t) == cid

    def test_same_term_same_class(self):
        eg = EGraph()
        t = Term(head="energy", children={"type": "kinetic", "joules": 500})
        c1 = eg.add(t, "atom_a")
        c2 = eg.add(t, "atom_b")
        assert c1 == c2

    def test_different_terms_different_classes(self):
        eg = EGraph()
        t1 = Term(head="energy", children={"joules": 500})
        t2 = Term(head="thermal", children={"watts": 200})
        c1 = eg.add(t1, "a")
        c2 = eg.add(t2, "b")
        assert c1 != c2

    def test_discover_relations(self, related_atoms):
        eg = EGraph()
        a, b = related_atoms
        for op_name, term_dict in a.all_terms():
            t = Term.from_dict(term_dict)
            eg.add(t, a.atom_id)
        for op_name, term_dict in b.all_terms():
            t = Term.from_dict(term_dict)
            eg.add(t, b.atom_id)

        relations = eg.discover_relations()
        assert len(relations) >= 1
        atom_ids = {relations[0][0], relations[0][1]}
        assert atom_ids == {"object_a", "object_b"}

    def test_merge_classes(self):
        eg = EGraph()
        t1 = Term(head="a", children={"x": 1})
        t2 = Term(head="b", children={"x": 2})
        c1 = eg.add(t1, "atom1")
        c2 = eg.add(t2, "atom2")
        merged = eg.merge(c1, c2)
        assert len(eg.classes) == 1
        assert eg.classes[merged].source_atoms == ["atom1", "atom2"]

    def test_clear(self):
        eg = EGraph()
        eg.add(Term(head="x"), "a")
        eg.clear()
        assert eg.stats()["classes"] == 0


# ---- Representation Generator ----

class TestGenerator:
    def test_deterministic(self, simple_atom):
        gen = RepresentationGenerator(default_dims=32)
        ctx = Context(domain="test", dimensions=32)
        r1 = gen.generate(simple_atom, ctx)
        r2 = gen.generate(simple_atom, ctx)
        np.testing.assert_array_equal(r1.vector, r2.vector)

    def test_context_changes_vector(self, simple_atom):
        gen = RepresentationGenerator(default_dims=32)
        r1 = gen.generate(simple_atom, Context(domain="physics", dimensions=32))
        r2 = gen.generate(simple_atom, Context(domain="chemistry", dimensions=32))
        assert not np.array_equal(r1.vector, r2.vector)

    def test_normalized_output(self, simple_atom):
        gen = RepresentationGenerator(default_dims=64)
        r = gen.generate(simple_atom)
        norm = float(np.linalg.norm(r.vector))
        assert abs(norm - 1.0) < 1e-5

    def test_ephemeral_size(self, simple_atom):
        gen = RepresentationGenerator(default_dims=64)
        r = gen.generate(simple_atom)
        assert r.dimensions == 64
        assert r.size_bytes() == 64 * 4  # float32


# ---- Adaptive Cache ----

class TestAdaptiveCache:
    def test_miss_then_hit(self, simple_atom):
        gen = RepresentationGenerator()
        cache = AdaptiveCache(max_entries=10)
        rep = gen.generate(simple_atom)

        assert cache.get(rep.atom_id, rep.context_hash) is None
        cache.put(rep)
        assert cache.get(rep.atom_id, rep.context_hash) is not None

    def test_eviction(self, simple_atom):
        cache = AdaptiveCache(max_entries=2)
        gen = RepresentationGenerator()

        atoms = [
            KnowledgeAtom(atom_id=f"a{i}", sigma={"v": i})
            for i in range(3)
        ]
        for a in atoms:
            cache.put(gen.generate(a))

        assert cache.stats()["entries"] == 2  # one was evicted

    def test_hit_rate(self):
        cache = AdaptiveCache()
        gen = RepresentationGenerator()
        atom = KnowledgeAtom(atom_id="x", sigma={"v": 1})
        rep = gen.generate(atom)
        cache.put(rep)

        cache.get(rep.atom_id, rep.context_hash)  # hit
        cache.get("missing", "nope")               # miss

        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5


# ---- Runtime ----

class TestRuntime:
    def test_register_and_query(self, simple_atom):
        runtime = DSRRuntime(default_dims=32)
        runtime.register(simple_atom)
        result = runtime.query(Query(intent="test"))
        assert result.atoms_evaluated == 1
        assert len(result.representations) == 1

    def test_targeted_query(self):
        runtime = DSRRuntime()
        a1 = KnowledgeAtom(atom_id="target", sigma={"x": 1})
        a2 = KnowledgeAtom(atom_id="other", sigma={"x": 2})
        runtime.register_many([a1, a2])
        result = runtime.query(Query(intent="test", targets=["target"]))
        assert result.atoms_evaluated == 1

    def test_emergent_relations(self, related_atoms):
        runtime = DSRRuntime()
        runtime.register_many(list(related_atoms))
        result = runtime.query(Query(intent="relate"))
        assert len(result.relations) >= 1

    def test_persistent_storage_minimal(self):
        runtime = DSRRuntime()
        for i in range(100):
            runtime.register(KnowledgeAtom(
                atom_id=f"n{i}",
                sigma={"type": "test", "idx": i},
            ))
        total = runtime.total_persistent_bytes()
        # 100 atoms should be well under 20KB
        assert total < 20_000

    def test_clear_all(self, simple_atom):
        runtime = DSRRuntime()
        runtime.register(simple_atom)
        runtime.query(Query(intent="test"))
        runtime.clear_all()
        assert runtime.atom_count == 0
        assert runtime.stats()["cache"]["entries"] == 0
