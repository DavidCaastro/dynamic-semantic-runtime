"""Dynamic Semantic Runtime — knowledge via on-demand generation."""

from dsr.atom import KnowledgeAtom, Constraint, Operator
from dsr.context import Query, Context
from dsr.generator import RepresentationGenerator
from dsr.egraph import EGraph, EClass, Term
from dsr.cache import AdaptiveCache
from dsr.runtime import DSRRuntime

__version__ = "0.1.0"

__all__ = [
    "KnowledgeAtom",
    "Constraint",
    "Operator",
    "Query",
    "Context",
    "RepresentationGenerator",
    "EGraph",
    "EClass",
    "Term",
    "AdaptiveCache",
    "DSRRuntime",
]
