"""Example: Vehicle Fleet Telemetry with DSR.

Demonstrates how physical knowledge (vehicle sensors, thermodynamics,
kinematics) can be represented as KnowledgeAtoms with invariant
constraints and transformation operators — without storing a single
relationship or embedding persistently.

Run:  python examples/vehicle_telemetry.py
"""

from dsr import (
    KnowledgeAtom,
    Constraint,
    Operator,
    Query,
    Context,
    DSRRuntime,
)


def build_fleet_atoms() -> list[KnowledgeAtom]:
    """Create atoms for a vehicle telemetry domain."""

    # --- Operators (pure functions) ---

    def kinetic_energy(sigma, ctx):
        m = sigma.get("mass_kg", 1000)
        v = ctx.get("velocity_ms", sigma.get("max_speed_ms", 30))
        return {"_head": "energy", "type": "kinetic", "joules": 0.5 * m * v ** 2}

    def thermal_load(sigma, ctx):
        temp = ctx.get("ambient_temp_c", 25)
        power_kw = sigma.get("power_kw", 100)
        return {"_head": "thermal", "type": "heat_dissipation", "watts": power_kw * 1000 * (1 - 0.35)}

    def braking_energy(sigma, ctx):
        m = sigma.get("mass_kg", 1000)
        v = ctx.get("velocity_ms", 30)
        return {"_head": "energy", "type": "kinetic", "joules": 0.5 * m * v ** 2}

    def fuel_consumption(sigma, ctx):
        power_kw = sigma.get("power_kw", 100)
        efficiency = sigma.get("efficiency", 0.35)
        return {"_head": "consumption", "liters_per_hour": power_kw / (efficiency * 34.2)}

    def tire_friction(sigma, ctx):
        m = sigma.get("mass_kg", 1000)
        mu = sigma.get("friction_coeff", 0.7)
        return {"_head": "thermal", "type": "heat_dissipation", "watts": mu * m * 9.81 * ctx.get("velocity_ms", 20)}

    # --- Constraints ---

    max_temp = Constraint("max_coolant_temp", lambda b: b.get("coolant_temp_c", 80) < 110)
    positive_mass = Constraint("positive_mass", lambda b: b.get("mass_kg", 1) > 0)

    # --- Atoms ---

    engine = KnowledgeAtom(
        atom_id="engine_v6_001",
        sigma={"type": "combustion_engine", "cylinders": 6, "power_kw": 200, "mass_kg": 180, "efficiency": 0.35},
        constraints=[max_temp, positive_mass],
        operators=[
            Operator("kinetic_energy", kinetic_energy),
            Operator("thermal_load", thermal_load),
            Operator("fuel_consumption", fuel_consumption),
        ],
        provenance="manufacturer_spec_v3",
        confidence=0.95,
    )

    brakes = KnowledgeAtom(
        atom_id="brake_system_001",
        sigma={"type": "disc_brake", "mass_kg": 45, "max_temp_c": 600, "friction_coeff": 0.4},
        constraints=[
            Constraint("brake_temp_limit", lambda b: b.get("disc_temp_c", 100) < 600),
        ],
        operators=[
            Operator("braking_energy", braking_energy),
            Operator("tire_friction", tire_friction),
        ],
        provenance="supplier_datasheet",
        confidence=0.90,
    )

    vehicle = KnowledgeAtom(
        atom_id="vehicle_sedan_001",
        sigma={"type": "sedan", "mass_kg": 1600, "max_speed_ms": 55, "drag_coeff": 0.28},
        constraints=[positive_mass],
        operators=[
            Operator("kinetic_energy", kinetic_energy),
        ],
        provenance="design_spec",
        confidence=0.98,
    )

    tire = KnowledgeAtom(
        atom_id="tire_front_001",
        sigma={"type": "tire", "mass_kg": 12, "friction_coeff": 0.7, "max_temp_c": 120},
        constraints=[
            Constraint("tire_temp_limit", lambda b: b.get("surface_temp_c", 60) < 120),
        ],
        operators=[
            Operator("tire_friction", tire_friction),
        ],
        provenance="tire_manufacturer",
        confidence=0.92,
    )

    return [engine, brakes, vehicle, tire]


def main():
    print("=" * 70)
    print("DSR Example: Vehicle Fleet Telemetry")
    print("=" * 70)

    # 1. Build runtime and register atoms
    runtime = DSRRuntime(default_dims=64)
    atoms = build_fleet_atoms()
    runtime.register_many(atoms)

    print(f"\nRegistered {runtime.atom_count} atoms")
    print(f"Total persistent storage: {runtime.total_persistent_bytes()} bytes")
    print()

    # 2. Query under highway context
    print("-" * 70)
    print("Query 1: Highway driving at 120 km/h")
    print("-" * 70)

    highway_ctx = Context(
        domain="vehicle_dynamics",
        dimensions=64,
        bindings={"velocity_ms": 33.3, "ambient_temp_c": 35},
    )

    result = runtime.query(
        Query(intent="analyze", targets=[]),  # all atoms
        highway_ctx,
    )

    print(f"  Atoms evaluated:     {result.atoms_evaluated}")
    print(f"  Generation time:     {result.generation_time_us:.0f} us")
    print(f"  E-Graph classes:     {result.egraph_stats['classes']}")
    print(f"  Relations discovered: {result.relations}")
    print()

    for rep in result.representations:
        print(f"  {rep.atom_id:25s} -> dims={rep.dimensions}, ctx={rep.context_hash[:8]}")

    # Show emergent relationships
    if result.relations:
        print("\n  Emergent relationships (no stored edges!):")
        for a, b, cid in result.relations:
            print(f"    {a} <-> {b}  (unified in E-Class {cid})")

    # 3. Query under city context (different embeddings for same atoms)
    print()
    print("-" * 70)
    print("Query 2: City driving at 40 km/h (same atoms, different context)")
    print("-" * 70)

    city_ctx = Context(
        domain="vehicle_dynamics",
        dimensions=64,
        bindings={"velocity_ms": 11.1, "ambient_temp_c": 22},
    )

    result2 = runtime.query(Query(intent="analyze"), city_ctx)

    print(f"  Atoms evaluated:     {result2.atoms_evaluated}")
    print(f"  Generation time:     {result2.generation_time_us:.0f} us")
    print(f"  Relations discovered: {len(result2.relations)}")

    # 4. Demonstrate context-dependent embeddings
    print()
    print("-" * 70)
    print("Context-dependent embeddings (same atom, different vectors)")
    print("-" * 70)

    for r1 in result.representations:
        for r2 in result2.representations:
            if r1.atom_id == r2.atom_id:
                sim = r1.cosine_similarity(r2)
                print(f"  {r1.atom_id:25s}: highway vs city cosine = {sim:.4f}")

    # 5. Cache stats
    print()
    print("-" * 70)
    print("Cache stats after 2 queries")
    print("-" * 70)
    cs = runtime.stats()["cache"]
    print(f"  Entries:      {cs['entries']}")
    print(f"  Hits:         {cs['hits']}")
    print(f"  Misses:       {cs['misses']}")
    print(f"  Hit rate:     {cs['hit_rate']:.1%}")
    print(f"  Memory (RAM): {cs['memory_bytes']} bytes")
    print()

    # 6. Constraint validation
    print("-" * 70)
    print("Constraint validation")
    print("-" * 70)
    engine = runtime.get_atom("engine_v6_001")
    print(f"  Engine at 80C coolant: valid = {engine.validate({'coolant_temp_c': 80, 'mass_kg': 180})}")
    print(f"  Engine at 115C coolant: valid = {engine.validate({'coolant_temp_c': 115, 'mass_kg': 180})}")
    print()

    print("=" * 70)
    print("Key insight: 0 edges stored, 0 embeddings persisted.")
    print(f"Total persistent footprint: {runtime.total_persistent_bytes()} bytes")
    print("=" * 70)


if __name__ == "__main__":
    main()
