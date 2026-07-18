"""E-Graph — Equality Saturation for semantic unification.

In DSR, relationships are NOT stored.  They are discovered at query time
by running atom operators and checking whether the resulting terms unify
in an E-Graph (Equality Graph).

Two atoms are related when their transformation operators produce terms
that belong to the same equivalence class.

This is a minimal, pure-Python E-Graph implementation sufficient for the
PoC.  Production systems would use optimized engines (e.g. egg in Rust).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Term:
    """A symbolic term produced by an atom operator.

    A term is a labeled tree: operator name + dictionary of children/values.
    Two terms unify if their heads match and their children recursively unify.
    """

    head: str
    children: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Term:
        """Build a Term from the dict returned by Operator.apply()."""
        head = d.get("_head", d.get("type", "unknown"))
        children = {k: v for k, v in d.items() if k not in ("_head", "type")}
        return Term(head=head, children=children)

    def structural_key(self) -> str:
        """Deterministic string key for structural matching."""
        parts = [self.head]
        for k in sorted(self.children):
            v = self.children[k]
            if isinstance(v, Term):
                parts.append(f"{k}={v.structural_key()}")
            else:
                parts.append(f"{k}={v!r}")
        return f"({' '.join(parts)})"

    def __repr__(self) -> str:
        return f"Term({self.head}, {self.children})"


@dataclass
class EClass:
    """An equivalence class — a set of terms considered semantically equal."""

    class_id: int
    terms: list[Term] = field(default_factory=list)
    source_atoms: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"EClass(id={self.class_id}, terms={len(self.terms)}, atoms={self.source_atoms})"


class EGraph:
    """Minimal E-Graph for term unification.

    Operations:
      - add(term, atom_id)      -> class_id
      - find(term)              -> class_id | None
      - merge(class_a, class_b) -> merged class_id
      - discover_relations()    -> list of (atom_a, atom_b, unifying_class)
    """

    def __init__(self) -> None:
        self._classes: dict[int, EClass] = {}
        self._key_to_class: dict[str, int] = {}
        self._next_id: int = 0

    @property
    def classes(self) -> dict[int, EClass]:
        return dict(self._classes)

    def _new_class_id(self) -> int:
        cid = self._next_id
        self._next_id += 1
        return cid

    def add(self, term: Term, atom_id: str = "") -> int:
        """Add a term to the E-Graph.  Returns its equivalence class ID.

        If a structurally identical term already exists, the atom_id is
        appended to that class (this is how relationships emerge).
        """
        key = term.structural_key()

        if key in self._key_to_class:
            cid = self._key_to_class[key]
            if atom_id and atom_id not in self._classes[cid].source_atoms:
                self._classes[cid].source_atoms.append(atom_id)
            return cid

        cid = self._new_class_id()
        ec = EClass(class_id=cid, terms=[term], source_atoms=[atom_id] if atom_id else [])
        self._classes[cid] = ec
        self._key_to_class[key] = cid
        return cid

    def find(self, term: Term) -> int | None:
        """Find the equivalence class of a term, or None."""
        return self._key_to_class.get(term.structural_key())

    def merge(self, class_a: int, class_b: int) -> int:
        """Merge two equivalence classes.  Returns the surviving class ID."""
        if class_a == class_b:
            return class_a
        ca, cb = self._classes[class_a], self._classes[class_b]
        # merge into the smaller ID
        survivor, absorbed = (ca, cb) if ca.class_id < cb.class_id else (cb, ca)
        survivor.terms.extend(absorbed.terms)
        for aid in absorbed.source_atoms:
            if aid not in survivor.source_atoms:
                survivor.source_atoms.append(aid)
        # re-point keys
        for key, cid in list(self._key_to_class.items()):
            if cid == absorbed.class_id:
                self._key_to_class[key] = survivor.class_id
        del self._classes[absorbed.class_id]
        return survivor.class_id

    def discover_relations(self) -> list[tuple[str, str, int]]:
        """Find all pairs of atoms that share an equivalence class.

        Returns [(atom_a, atom_b, class_id), ...] — these are the
        *emergent* relationships that DSR generates without persistence.
        """
        relations: list[tuple[str, str, int]] = []
        for cid, ec in self._classes.items():
            atoms = ec.source_atoms
            for i in range(len(atoms)):
                for j in range(i + 1, len(atoms)):
                    relations.append((atoms[i], atoms[j], cid))
        return relations

    def stats(self) -> dict[str, int]:
        total_terms = sum(len(ec.terms) for ec in self._classes.values())
        return {
            "classes": len(self._classes),
            "terms": total_terms,
            "relations_discovered": len(self.discover_relations()),
        }

    def clear(self) -> None:
        """Discard all state — the E-Graph returns to empty."""
        self._classes.clear()
        self._key_to_class.clear()
        self._next_id = 0
