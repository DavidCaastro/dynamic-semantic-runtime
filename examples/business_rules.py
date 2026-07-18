"""Example: API Business Logic with DSR.

Demonstrates how business domain rules (user roles, state transitions,
data validation) can be encoded as KnowledgeAtoms — the invariants of
the business — while all derived state (permissions, workflows,
validations) is generated on demand.

Run:  python examples/business_rules.py
"""

from dsr import (
    KnowledgeAtom,
    Constraint,
    Operator,
    Query,
    Context,
    DSRRuntime,
)


def build_business_atoms() -> list[KnowledgeAtom]:
    """Create atoms for an API business logic domain."""

    # --- Operators ---

    def permission_set(sigma, ctx):
        role = sigma.get("role", "viewer")
        perms = {"viewer": 1, "editor": 3, "admin": 7, "owner": 15}
        level = perms.get(role, 0)
        return {"_head": "access", "type": "permission", "level": level, "role": role}

    def state_transition(sigma, ctx):
        current = ctx.get("current_state", sigma.get("initial_state", "draft"))
        transitions = sigma.get("transitions", {})
        next_states = transitions.get(current, [])
        return {"_head": "workflow", "type": "transition", "from": current, "to": str(next_states)}

    def data_validation(sigma, ctx):
        entity_type = sigma.get("entity_type", "unknown")
        required = sigma.get("required_fields", [])
        return {"_head": "validation", "type": "schema", "entity": entity_type, "fields": len(required)}

    def audit_requirement(sigma, ctx):
        sensitivity = sigma.get("sensitivity", "low")
        levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        return {"_head": "audit", "type": "compliance", "level": levels.get(sensitivity, 0)}

    def rate_limit(sigma, ctx):
        role = sigma.get("role", "viewer")
        limits = {"viewer": 100, "editor": 500, "admin": 2000, "owner": 10000}
        return {"_head": "access", "type": "permission", "level": limits.get(role, 100) // 100, "role": role}

    # --- Constraints ---

    valid_role = Constraint("valid_role", lambda b: b.get("role") in ("viewer", "editor", "admin", "owner"))
    non_empty_name = Constraint("non_empty_name", lambda b: len(b.get("name", "")) > 0)

    # --- Atoms ---

    admin_role = KnowledgeAtom(
        atom_id="role_admin",
        sigma={"type": "role", "role": "admin", "sensitivity": "high"},
        constraints=[valid_role],
        operators=[
            Operator("permission_set", permission_set),
            Operator("audit_requirement", audit_requirement),
            Operator("rate_limit", rate_limit),
        ],
        provenance="rbac_policy_v2",
        confidence=1.0,
    )

    editor_role = KnowledgeAtom(
        atom_id="role_editor",
        sigma={"type": "role", "role": "editor", "sensitivity": "medium"},
        constraints=[valid_role],
        operators=[
            Operator("permission_set", permission_set),
            Operator("audit_requirement", audit_requirement),
            Operator("rate_limit", rate_limit),
        ],
        provenance="rbac_policy_v2",
        confidence=1.0,
    )

    invoice_entity = KnowledgeAtom(
        atom_id="entity_invoice",
        sigma={
            "type": "entity",
            "entity_type": "invoice",
            "required_fields": ["amount", "currency", "vendor_id", "date"],
            "initial_state": "draft",
            "transitions": {
                "draft": ["submitted"],
                "submitted": ["approved", "rejected"],
                "approved": ["paid"],
                "rejected": ["draft"],
                "paid": [],
            },
            "sensitivity": "high",
        },
        constraints=[non_empty_name],
        operators=[
            Operator("state_transition", state_transition),
            Operator("data_validation", data_validation),
            Operator("audit_requirement", audit_requirement),
        ],
        provenance="domain_model_v3",
        confidence=0.98,
    )

    order_entity = KnowledgeAtom(
        atom_id="entity_order",
        sigma={
            "type": "entity",
            "entity_type": "order",
            "required_fields": ["product_id", "quantity", "customer_id"],
            "initial_state": "pending",
            "transitions": {
                "pending": ["confirmed", "cancelled"],
                "confirmed": ["shipped"],
                "shipped": ["delivered"],
                "cancelled": [],
                "delivered": [],
            },
            "sensitivity": "medium",
        },
        constraints=[non_empty_name],
        operators=[
            Operator("state_transition", state_transition),
            Operator("data_validation", data_validation),
            Operator("audit_requirement", audit_requirement),
        ],
        provenance="domain_model_v3",
        confidence=0.97,
    )

    return [admin_role, editor_role, invoice_entity, order_entity]


def main():
    print("=" * 70)
    print("DSR Example: API Business Logic")
    print("=" * 70)

    runtime = DSRRuntime(default_dims=64)
    atoms = build_business_atoms()
    runtime.register_many(atoms)

    print(f"\nRegistered {runtime.atom_count} atoms")
    print(f"Total persistent storage: {runtime.total_persistent_bytes()} bytes")

    # --- Query 1: Roles under compliance audit context ---
    print()
    print("-" * 70)
    print("Query 1: Who needs audit under compliance review?")
    print("-" * 70)

    compliance_ctx = Context(
        domain="compliance",
        dimensions=64,
        bindings={"audit_mode": True},
    )

    result = runtime.query(Query(intent="audit_check"), compliance_ctx)

    print(f"  Atoms evaluated: {result.atoms_evaluated}")
    print(f"  Generation time: {result.generation_time_us:.0f} us")

    if result.relations:
        print("\n  Emergent relationships:")
        for a, b, cid in result.relations:
            print(f"    {a} <-> {b}  (E-Class {cid})")
    else:
        print("\n  No emergent relationships (atoms have distinct operator signatures)")

    # --- Query 2: State transitions for invoice in 'submitted' state ---
    print()
    print("-" * 70)
    print("Query 2: Invoice state transitions from 'submitted'")
    print("-" * 70)

    workflow_ctx = Context(
        domain="workflow",
        dimensions=64,
        bindings={"current_state": "submitted"},
    )

    result2 = runtime.query(
        Query(intent="transition", targets=["entity_invoice"]),
        workflow_ctx,
    )

    invoice = runtime.get_atom("entity_invoice")
    term = invoice.apply_operator("state_transition", workflow_ctx.to_dict())
    print(f"  Transition from 'submitted': {term}")

    # --- Query 3: Different context = different embeddings ---
    print()
    print("-" * 70)
    print("Context-dependent representations")
    print("-" * 70)

    ctx_a = Context(domain="security", dimensions=64)
    ctx_b = Context(domain="performance", dimensions=64)

    res_a = runtime.query(Query(intent="analyze", targets=["role_admin"]), ctx_a)
    res_b = runtime.query(Query(intent="analyze", targets=["role_admin"]), ctx_b)

    if res_a.representations and res_b.representations:
        sim = res_a.representations[0].cosine_similarity(res_b.representations[0])
        print(f"  role_admin under 'security' vs 'performance': cosine = {sim:.4f}")
        print("  (Different contexts produce different vector representations)")

    # --- Stats ---
    print()
    print("-" * 70)
    print("Runtime stats")
    print("-" * 70)
    stats = runtime.stats()
    print(f"  Atoms:            {stats['atoms']}")
    print(f"  Persistent bytes: {stats['persistent_bytes']}")
    print(f"  Cache entries:    {stats['cache']['entries']}")
    print(f"  Cache hit rate:   {stats['cache']['hit_rate']:.1%}")
    print(f"  Cache RAM:        {stats['cache']['memory_bytes']} bytes")
    print()

    print("=" * 70)
    print("Key insight: business rules as invariants, everything else generated.")
    print(f"Total persistent footprint: {stats['persistent_bytes']} bytes")
    print("=" * 70)


if __name__ == "__main__":
    main()
